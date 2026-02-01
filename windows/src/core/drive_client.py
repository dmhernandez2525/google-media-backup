"""
Google Drive API client for listing and downloading files.
Supports videos and documents with Google Docs export functionality.
"""

import io
import os
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from .google_auth import get_auth_manager
from utils.logger import get_logger
from utils.config import FileState

logger = get_logger()


# Video MIME types to download
VIDEO_MIME_TYPES = [
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
    "video/3gpp",
    "video/mpeg",
    "video/x-matroska",
    "video/x-ms-wmv",
    "video/x-flv",
]

# Document MIME types to download
DOCUMENT_MIME_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
]

# Google Workspace MIME types and their export formats
GOOGLE_DOCS_EXPORT = {
    "application/vnd.google-apps.document": (
        "application/pdf",
        ".pdf"
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx"
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx"
    ),
}


class DriveClient:
    """Client for interacting with Google Drive API."""

    def __init__(self):
        self._service = None
        self._should_stop = False

    def _get_service(self):
        """Get or create the Drive API service."""
        if self._service is not None:
            return self._service

        auth_manager = get_auth_manager()
        credentials = auth_manager.credentials

        if credentials is None:
            raise RuntimeError("Not authenticated with Google")

        self._service = build("drive", "v3", credentials=credentials)
        return self._service

    def invalidate_service(self) -> None:
        """Invalidate the cached service (call after re-auth)."""
        self._service = None

    def list_all_videos_and_documents(
        self,
        include_videos: bool = True,
        include_documents: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[FileState]:
        """
        List all videos and documents from Google Drive.

        Args:
            include_videos: Include video files
            include_documents: Include document files
            progress_callback: Optional callback(current_count, total_estimated)

        Returns:
            List of FileState objects for each file
        """
        service = self._get_service()
        files: List[FileState] = []

        # Build MIME type query
        mime_queries = []

        if include_videos:
            for mime in VIDEO_MIME_TYPES:
                mime_queries.append(f"mimeType='{mime}'")

        if include_documents:
            for mime in DOCUMENT_MIME_TYPES:
                mime_queries.append(f"mimeType='{mime}'")
            # Include Google Workspace docs for export
            for mime in GOOGLE_DOCS_EXPORT.keys():
                mime_queries.append(f"mimeType='{mime}'")

        if not mime_queries:
            return files

        query = f"({' or '.join(mime_queries)}) and trashed=false"

        page_token = None
        page_count = 0

        try:
            while True:
                # Request files with pagination
                results = service.files().list(
                    q=query,
                    pageSize=100,
                    pageToken=page_token,
                    fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)"
                ).execute()

                items = results.get("files", [])
                page_count += 1

                for item in items:
                    file_state = FileState(
                        id=item["id"],
                        name=item["name"],
                        source="drive",
                        mime_type=item.get("mimeType", ""),
                        size=int(item.get("size", 0)),
                        status="pending"
                    )
                    files.append(file_state)

                if progress_callback:
                    progress_callback(len(files), len(files))

                logger.debug(f"Listed {len(items)} files from page {page_count}")

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            logger.info(f"Found {len(files)} files in Google Drive")
            return files

        except HttpError as e:
            logger.error(f"Error listing Drive files: {e}")
            raise

    def download_file(
        self,
        file_id: str,
        destination: Path,
        mime_type: str = "",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Download a file from Google Drive.

        Args:
            file_id: The Drive file ID
            destination: Local path to save the file
            mime_type: MIME type of the file (for determining export)
            progress_callback: Optional callback(bytes_downloaded, total_bytes)

        Returns:
            True if download was successful
        """
        service = self._get_service()

        try:
            # Check if this is a Google Workspace file that needs export
            if mime_type in GOOGLE_DOCS_EXPORT:
                return self._export_file(file_id, destination, mime_type, progress_callback)

            # Regular file download
            request = service.files().get_media(fileId=file_id)

            # Ensure parent directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            with open(destination, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False

                while not done:
                    status, done = downloader.next_chunk()

                    if status and progress_callback:
                        progress = int(status.progress() * 100)
                        progress_callback(progress, 100)

            # Validate file was downloaded properly (not empty)
            if destination.exists() and destination.stat().st_size == 0:
                logger.warning(f"Downloaded file is empty, removing: {destination}")
                destination.unlink()
                return False

            logger.debug(f"Downloaded file to {destination}")
            return True

        except HttpError as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            # Clean up partial file
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading file: {e}")
            # Clean up partial file
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            return False

    def _export_file(
        self,
        file_id: str,
        destination: Path,
        source_mime_type: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Export a Google Workspace file to a downloadable format.

        Args:
            file_id: The Drive file ID
            destination: Local path to save the file
            source_mime_type: Original Google Workspace MIME type
            progress_callback: Optional callback(bytes_downloaded, total_bytes)

        Returns:
            True if export was successful
        """
        service = self._get_service()

        if source_mime_type not in GOOGLE_DOCS_EXPORT:
            logger.warning(f"Unknown export type: {source_mime_type}")
            return False

        export_mime, extension = GOOGLE_DOCS_EXPORT[source_mime_type]

        # Update destination with correct extension
        if not str(destination).lower().endswith(extension.lower()):
            destination = destination.with_suffix(extension)

        try:
            request = service.files().export_media(
                fileId=file_id,
                mimeType=export_mime
            )

            # Ensure parent directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            with open(destination, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False

                while not done:
                    status, done = downloader.next_chunk()

                    if status and progress_callback:
                        progress = int(status.progress() * 100)
                        progress_callback(progress, 100)

            # Validate file was exported properly (not empty)
            if destination.exists() and destination.stat().st_size == 0:
                logger.warning(f"Exported file is empty, removing: {destination}")
                destination.unlink()
                return False

            logger.debug(f"Exported file to {destination}")
            return True

        except HttpError as e:
            logger.error(f"Error exporting file {file_id}: {e}")
            # Clean up partial file
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            return False
        except Exception as e:
            logger.error(f"Unexpected error exporting file: {e}")
            # Clean up partial file
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            return False

    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific file.

        Args:
            file_id: The Drive file ID

        Returns:
            File metadata dict or None if not found
        """
        service = self._get_service()

        try:
            return service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime"
            ).execute()
        except HttpError as e:
            logger.error(f"Error getting file info: {e}")
            return None

    def stop(self) -> None:
        """Signal to stop ongoing operations."""
        self._should_stop = True

    def reset(self) -> None:
        """Reset state for new operations."""
        self._should_stop = False


# Singleton instance
_drive_client: Optional[DriveClient] = None


def get_drive_client() -> DriveClient:
    """Get the global DriveClient instance."""
    global _drive_client
    if _drive_client is None:
        _drive_client = DriveClient()
    return _drive_client
