"""
Download manager for orchestrating file downloads from Google Drive and Photos.
Handles parallel scanning, sequential downloading, pause/resume, and state persistence.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict

from .google_auth import get_auth_manager
from .drive_client import get_drive_client, VIDEO_MIME_TYPES, GOOGLE_DOCS_EXPORT
from .photos_client import get_photos_client
from utils.config import get_config_manager, FileState, DownloadStats
from utils.paths import Paths
from utils.logger import get_logger
from utils.notifications import (
    notify_download_started,
    notify_download_complete,
    notify_download_error
)

logger = get_logger()


class DownloadManager:
    """Manages downloading files from Google Drive and Photos."""

    def __init__(self):
        self._is_downloading = False
        self._is_paused = False
        self._should_stop = False
        self._current_file: Optional[str] = None
        self._download_thread: Optional[threading.Thread] = None

        # Callbacks
        self._on_progress: Optional[Callable[[str, int, int], None]] = None
        self._on_file_complete: Optional[Callable[[FileState], None]] = None
        self._on_download_complete: Optional[Callable[[DownloadStats], None]] = None
        self._on_error: Optional[Callable[[str, str], None]] = None

    @property
    def is_downloading(self) -> bool:
        """Check if downloads are in progress."""
        return self._is_downloading

    @property
    def is_paused(self) -> bool:
        """Check if downloads are paused."""
        return self._is_paused

    @property
    def current_file(self) -> Optional[str]:
        """Get the name of the file currently being downloaded."""
        return self._current_file

    def set_progress_callback(self, callback: Callable[[str, int, int], None]) -> None:
        """Set callback for download progress updates."""
        self._on_progress = callback

    def set_file_complete_callback(self, callback: Callable[[FileState], None]) -> None:
        """Set callback for when a file download completes."""
        self._on_file_complete = callback

    def set_download_complete_callback(self, callback: Callable[[DownloadStats], None]) -> None:
        """Set callback for when all downloads complete."""
        self._on_download_complete = callback

    def set_error_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for download errors."""
        self._on_error = callback

    def scan_sources(
        self,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> DownloadStats:
        """
        Scan Google Drive and Photos for files to download.

        Args:
            progress_callback: Optional callback(source_name, file_count)

        Returns:
            Statistics about found files
        """
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated:
            raise RuntimeError("Not authenticated with Google")

        config_manager = get_config_manager()
        config = config_manager.get_config()

        drive_files: List[FileState] = []
        photos_files: List[FileState] = []
        errors: List[str] = []

        # Scan Drive and Photos in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}

            # Submit Drive scan
            if config.download_videos or config.download_documents:
                futures[executor.submit(
                    self._scan_drive,
                    config.download_videos,
                    config.download_documents
                )] = "drive"

            # Submit Photos scan
            if config.download_photos and config.download_videos:
                futures[executor.submit(self._scan_photos)] = "photos"

            # Collect results
            for future in as_completed(futures):
                source = futures[future]
                try:
                    files = future.result()
                    if source == "drive":
                        drive_files = files
                        if progress_callback:
                            progress_callback("Google Drive", len(files))
                    else:
                        photos_files = files
                        if progress_callback:
                            progress_callback("Google Photos", len(files))
                except Exception as e:
                    logger.error(f"Error scanning {source}: {e}")
                    errors.append(f"{source}: {e}")

        # Update state with found files
        drive_state = config_manager.get_drive_state()
        photos_state = config_manager.get_photos_state()

        # Add new files (preserve existing state for already-known files)
        for file in drive_files:
            if file.id not in drive_state:
                drive_state[file.id] = file
            else:
                # Update metadata but preserve status
                existing = drive_state[file.id]
                file.status = existing.status
                file.downloaded_at = existing.downloaded_at
                file.local_path = existing.local_path
                drive_state[file.id] = file

        for file in photos_files:
            if file.id not in photos_state:
                photos_state[file.id] = file
            else:
                existing = photos_state[file.id]
                file.status = existing.status
                file.downloaded_at = existing.downloaded_at
                file.local_path = existing.local_path
                photos_state[file.id] = file

        # Save state
        config_manager.save_drive_state()
        config_manager.save_photos_state()

        # Return stats
        return config_manager.get_download_stats()

    def _scan_drive(self, include_videos: bool, include_documents: bool) -> List[FileState]:
        """Scan Google Drive for files."""
        drive_client = get_drive_client()
        return drive_client.list_all_videos_and_documents(
            include_videos=include_videos,
            include_documents=include_documents
        )

    def _scan_photos(self) -> List[FileState]:
        """Scan Google Photos for videos."""
        photos_client = get_photos_client()
        return photos_client.list_all_videos()

    def start_download(self) -> None:
        """Start downloading pending files in background thread."""
        if self._is_downloading:
            logger.warning("Download already in progress")
            return

        self._is_downloading = True
        self._is_paused = False
        self._should_stop = False

        self._download_thread = threading.Thread(
            target=self._download_worker,
            daemon=True
        )
        self._download_thread.start()

    def pause_download(self) -> None:
        """Pause the current download."""
        if not self._is_downloading:
            return
        self._is_paused = True
        logger.info("Download paused")

    def resume_download(self) -> None:
        """Resume a paused download."""
        if not self._is_downloading:
            return
        self._is_paused = False
        logger.info("Download resumed")

    def stop_download(self) -> None:
        """Stop the download completely."""
        if not self._is_downloading:
            return

        self._should_stop = True
        self._is_paused = False

        # Stop the clients
        get_drive_client().stop()
        get_photos_client().stop()

        # Wait for thread to finish
        if self._download_thread and self._download_thread.is_alive():
            self._download_thread.join(timeout=5.0)

        self._is_downloading = False
        logger.info("Download stopped")

    def reset(self) -> None:
        """Reset state for new operations."""
        self._is_downloading = False
        self._is_paused = False
        self._should_stop = False
        self._current_file = None
        get_drive_client().reset()
        get_photos_client().reset()

    def _download_worker(self) -> None:
        """Worker thread for downloading files."""
        config_manager = get_config_manager()
        config = config_manager.get_config()
        download_path = Path(config.download_path)

        # Get all pending files
        drive_state = config_manager.get_drive_state()
        photos_state = config_manager.get_photos_state()

        pending_files: List[tuple] = []  # (file_state, source_type)

        for file_id, file_state in drive_state.items():
            if file_state.status == "pending":
                pending_files.append((file_state, "drive"))

        for file_id, file_state in photos_state.items():
            if file_state.status == "pending":
                pending_files.append((file_state, "photos"))

        if not pending_files:
            logger.info("No pending files to download")
            self._is_downloading = False
            if self._on_download_complete:
                self._on_download_complete(config_manager.get_download_stats())
            return

        notify_download_started(len(pending_files))
        downloaded_count = 0
        skipped_count = 0
        error_count = 0

        for file_state, source_type in pending_files:
            # Check for stop/pause
            if self._should_stop:
                break

            while self._is_paused:
                if self._should_stop:
                    break
                threading.Event().wait(0.5)

            if self._should_stop:
                break

            # Download the file
            self._current_file = file_state.name
            success, was_skipped = self._download_single_file(file_state, source_type, download_path)

            if success:
                if was_skipped:
                    skipped_count += 1
                else:
                    downloaded_count += 1
                file_state.status = "complete"
                file_state.downloaded_at = datetime.now().isoformat()

                if self._on_file_complete:
                    self._on_file_complete(file_state)
            else:
                error_count += 1
                file_state.status = "error"

            # Update state
            if source_type == "drive":
                config_manager.update_drive_file(file_state)
            else:
                config_manager.update_photos_file(file_state)

        self._current_file = None
        self._is_downloading = False

        stats = config_manager.get_download_stats()
        notify_download_complete(downloaded_count, skipped_count, error_count)

        if self._on_download_complete:
            self._on_download_complete(stats)

    def _download_single_file(
        self,
        file_state: FileState,
        source_type: str,
        download_path: Path
    ) -> tuple:
        """
        Download a single file.

        Returns:
            Tuple of (success: bool, was_skipped: bool)
        """
        try:
            # Determine destination directory
            if file_state.mime_type.startswith("video/") or file_state.mime_type in GOOGLE_DOCS_EXPORT:
                if source_type == "drive":
                    if file_state.mime_type.startswith("video/"):
                        dest_dir = Paths.get_drive_videos_dir(download_path)
                    else:
                        dest_dir = Paths.get_documents_dir(download_path)
                else:
                    dest_dir = Paths.get_photos_videos_dir(download_path)
            else:
                dest_dir = Paths.get_documents_dir(download_path)

            # Create destination path
            destination = dest_dir / file_state.name

            # Check if file already exists (skip)
            if destination.exists():
                logger.debug(f"File already exists: {destination}")
                file_state.local_path = str(destination)
                return True, True  # Success, was skipped

            # Progress callback wrapper
            def progress_cb(current: int, total: int):
                if self._on_progress:
                    self._on_progress(file_state.name, current, total)

            # Download based on source
            if source_type == "drive":
                drive_client = get_drive_client()
                success = drive_client.download_file(
                    file_state.id,
                    destination,
                    file_state.mime_type,
                    progress_cb
                )
            else:
                photos_client = get_photos_client()
                success = photos_client.download_video(
                    file_state.id,
                    destination,
                    progress_cb
                )

            if success:
                file_state.local_path = str(destination)
                logger.info(f"Downloaded: {file_state.name}")
            else:
                file_state.error_message = "Download failed"
                if self._on_error:
                    self._on_error(file_state.name, "Download failed")
                notify_download_error(file_state.name, "Download failed")

            return success, False  # Success/fail, not skipped

        except Exception as e:
            logger.error(f"Error downloading {file_state.name}: {e}")
            file_state.error_message = str(e)
            if self._on_error:
                self._on_error(file_state.name, str(e))
            notify_download_error(file_state.name, str(e))
            return False, False  # Failed, not skipped

    def get_statistics(self) -> DownloadStats:
        """Get current download statistics."""
        return get_config_manager().get_download_stats()

    def get_pending_files(self) -> List[FileState]:
        """Get list of pending files."""
        config_manager = get_config_manager()
        pending = []

        for file_state in config_manager.get_drive_state().values():
            if file_state.status == "pending":
                pending.append(file_state)

        for file_state in config_manager.get_photos_state().values():
            if file_state.status == "pending":
                pending.append(file_state)

        return pending

    def get_completed_files(self) -> List[FileState]:
        """Get list of completed files."""
        config_manager = get_config_manager()
        completed = []

        for file_state in config_manager.get_drive_state().values():
            if file_state.status == "complete":
                completed.append(file_state)

        for file_state in config_manager.get_photos_state().values():
            if file_state.status == "complete":
                completed.append(file_state)

        return completed


# Singleton instance
_download_manager: Optional[DownloadManager] = None


def get_download_manager() -> DownloadManager:
    """Get the global DownloadManager instance."""
    global _download_manager
    if _download_manager is None:
        _download_manager = DownloadManager()
    return _download_manager
