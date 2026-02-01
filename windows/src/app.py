"""
Main application controller for Google Media Backup.
Coordinates all components and manages application lifecycle.
"""

import os
import sys
import subprocess
import threading
from pathlib import Path
from typing import Optional

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    import tkinter as tk
    CTK_AVAILABLE = False

from core.google_auth import get_auth_manager
from core.drive_client import get_drive_client
from core.photos_client import get_photos_client
from core.download_manager import get_download_manager
from core.transcription import get_transcription_manager
# from ui.system_tray import get_system_tray  # Not used - Windows uses main window
from ui.main_window import get_main_window
from ui.auth_window import show_auth_dialog
from ui.config_window import show_config_dialog
from ui.progress_dialog import show_progress
from utils.config import get_config_manager
from utils.paths import Paths
from utils.logger import get_logger
from utils.notifications import (
    notify_signed_in,
    notify_sign_in_required,
    notify_download_stopped,
    notify_transcription_stopped
)

logger = get_logger()


class GoogleMediaBackupApp:
    """Main application controller."""

    def __init__(self):
        self._root: Optional[ctk.CTk] = None
        self._is_running = False

        # Get component instances
        self._auth_manager = get_auth_manager()
        self._download_manager = get_download_manager()
        self._transcription_manager = get_transcription_manager()
        self._main_window = get_main_window()
        self._config_manager = get_config_manager()

        # Setup callbacks
        self._setup_callbacks()

    def _setup_callbacks(self) -> None:
        """Set up callbacks between components."""
        # Auth callbacks
        self._auth_manager.set_auth_change_callback(self._on_auth_changed)

        # Download manager callbacks
        self._download_manager.set_progress_callback(self._on_download_progress)
        self._download_manager.set_file_complete_callback(self._on_file_complete)
        self._download_manager.set_download_complete_callback(self._on_download_complete)
        self._download_manager.set_error_callback(self._on_download_error)

        # Transcription callbacks
        self._transcription_manager.set_progress_callback(self._on_transcription_progress)
        self._transcription_manager.set_complete_callback(self._on_transcription_complete)
        self._transcription_manager.set_error_callback(self._on_transcription_error)

        # Main window callbacks
        self._main_window.set_callbacks(
            on_sign_in=self._handle_sign_in,
            on_sign_out=self._handle_sign_out,
            on_start_download=self._handle_start_download,
            on_stop_download=self._handle_stop_download,
            on_pause_download=self._handle_pause_download,
            on_resume_download=self._handle_resume_download,
            on_scan=self._handle_scan,
            on_transcribe=self._handle_transcribe,
            on_stop_transcription=self._handle_stop_transcription,
            on_open_folder=self._handle_open_folder,
            on_preferences=self._handle_preferences
        )

    def run(self) -> None:
        """Start the application."""
        logger.info("Starting Google Media Backup")
        logger.info(f"CTK_AVAILABLE: {CTK_AVAILABLE}")

        # Ensure directories exist
        logger.info("Ensuring directories exist...")
        Paths.ensure_all_directories()

        # Initialize state
        logger.info("Initializing state...")
        self._update_state()

        # Show main window on startup (Windows UX - visible in taskbar)
        logger.info("Showing main window...")
        self._main_window.show()

        # Get the root window from main_window
        self._root = self._main_window.window
        logger.info("Main window shown")

        # Override close behavior - minimize to taskbar instead of quit
        if self._root:
            self._root.protocol("WM_DELETE_WINDOW", self._handle_window_close)

        # Check if we should auto-download (with 1 second delay like macOS)
        config = self._config_manager.get_config()
        if config.auto_download and self._auth_manager.is_authenticated:
            logger.info("Auto-download enabled, scheduling...")
            self._root.after(1000, self._handle_start_download)

        # Run the main loop
        logger.info("Entering main loop...")
        self._is_running = True
        try:
            self._root.mainloop()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
        finally:
            logger.info("Exiting main loop, cleaning up...")
            self._cleanup()

    def _handle_window_close(self) -> None:
        """Handle window close button - ask to quit or minimize."""
        if self._download_manager.is_downloading or self._transcription_manager.is_transcribing:
            # If work in progress, ask what to do
            from tkinter import messagebox
            result = messagebox.askyesnocancel(
                "Close Window",
                "Download or transcription in progress.\n\n"
                "Yes = Stop and Quit\n"
                "No = Minimize (keep running)\n"
                "Cancel = Stay open"
            )
            if result is True:  # Yes - quit
                self._handle_quit()
            elif result is False:  # No - minimize
                self._root.iconify()
            # Cancel - do nothing
        else:
            # No work in progress - just quit
            self._handle_quit()

    def _cleanup(self) -> None:
        """Clean up resources on shutdown."""
        logger.info("Shutting down Google Media Backup")

        # Stop downloads/transcriptions
        self._download_manager.stop_download()
        self._transcription_manager.stop_transcription()

        self._is_running = False

    def _update_state(self) -> None:
        """Update component states."""
        is_auth = self._auth_manager.is_authenticated
        is_downloading = self._download_manager.is_downloading
        is_paused = self._download_manager.is_paused
        stats = self._download_manager.get_statistics()

        # Update main window
        self._main_window.update_state(
            is_authenticated=is_auth,
            is_downloading=is_downloading,
            is_paused=is_paused,
            is_transcribing=self._transcription_manager.is_transcribing,
            stats=stats
        )

    # Auth callbacks
    def _on_auth_changed(self, is_authenticated: bool) -> None:
        """Handle authentication state change."""
        if is_authenticated:
            notify_signed_in()
            # Invalidate cached services
            get_drive_client().invalidate_service()
            get_photos_client().invalidate_service()

        self._update_state()

    # Download callbacks
    def _on_download_progress(self, filename: str, current: int, total: int) -> None:
        """Handle download progress update."""
        logger.debug(f"Downloading {filename}: {current}%")

    def _on_file_complete(self, file_state) -> None:
        """Handle file download completion."""
        logger.info(f"Downloaded: {file_state.name}")
        self._update_state()

    def _on_download_complete(self, stats) -> None:
        """Handle all downloads completion."""
        logger.info(f"Download complete: {stats.downloaded} files")
        self._update_state()

        # Auto-transcribe if enabled
        config = self._config_manager.get_config()
        if config.auto_transcribe:
            pending = self._transcription_manager.get_pending_count()
            if pending > 0:
                self._transcription_manager.transcribe_all_pending()

    def _on_download_error(self, filename: str, error: str) -> None:
        """Handle download error."""
        logger.error(f"Download error for {filename}: {error}")

    # Transcription callbacks
    def _on_transcription_progress(self, filename: str, progress: float) -> None:
        """Handle transcription progress."""
        logger.debug(f"Transcribing {filename}: {progress:.0%}")

    def _on_transcription_complete(self, video_path: str, transcript_path: str) -> None:
        """Handle transcription completion."""
        logger.info(f"Transcribed: {video_path}")
        self._update_state()

    def _on_transcription_error(self, video_path: str, error: str) -> None:
        """Handle transcription error."""
        logger.error(f"Transcription error for {video_path}: {error}")

    # UI action handlers
    def _handle_sign_in(self) -> None:
        """Handle sign in request."""
        def on_complete(success: bool, message: str):
            self._update_state()

        show_auth_dialog(self._root, on_complete)

    def _handle_sign_out(self) -> None:
        """Handle sign out request."""
        self._auth_manager.sign_out()
        self._update_state()

    def _handle_start_download(self) -> None:
        """Handle start download request."""
        if not self._auth_manager.is_authenticated:
            notify_sign_in_required()
            return

        # Scan and download in background
        def scan_and_download():
            try:
                # Show progress
                if self._root:
                    self._root.after(0, lambda: self._show_scan_progress())

                # Scan sources
                self._download_manager.scan_sources()

                # Hide progress
                if self._root:
                    self._root.after(0, lambda: self._hide_scan_progress())

                # Start download
                self._download_manager.start_download()
                self._update_state()

            except Exception as e:
                logger.error(f"Error starting download: {e}")
                if self._root:
                    self._root.after(0, lambda: self._hide_scan_progress())

        thread = threading.Thread(target=scan_and_download, daemon=True)
        thread.start()

    def _handle_stop_download(self) -> None:
        """Handle stop download request."""
        self._download_manager.stop_download()
        notify_download_stopped()
        self._update_state()

    def _handle_pause_download(self) -> None:
        """Handle pause download request."""
        self._download_manager.pause_download()
        self._update_state()

    def _handle_resume_download(self) -> None:
        """Handle resume download request."""
        self._download_manager.resume_download()
        self._update_state()

    def _handle_scan(self) -> None:
        """Handle scan sources request."""
        if not self._auth_manager.is_authenticated:
            notify_sign_in_required()
            return

        def scan():
            try:
                if self._root:
                    self._root.after(0, lambda: self._show_scan_progress())

                self._download_manager.scan_sources()
                self._update_state()

            except Exception as e:
                logger.error(f"Error scanning: {e}")
            finally:
                if self._root:
                    self._root.after(0, lambda: self._hide_scan_progress())

        thread = threading.Thread(target=scan, daemon=True)
        thread.start()

    def _handle_transcribe(self) -> None:
        """Handle transcribe request."""
        self._transcription_manager.transcribe_all_pending()
        self._update_state()

    def _handle_stop_transcription(self) -> None:
        """Handle stop transcription request."""
        self._transcription_manager.stop_transcription()
        notify_transcription_stopped()
        self._update_state()

    def _handle_open_folder(self) -> None:
        """Handle open folder request."""
        config = self._config_manager.get_config()
        folder = Path(config.download_path)

        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)

        # Open in Windows Explorer
        try:
            os.startfile(str(folder))
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")
            # Fallback
            subprocess.run(["explorer", str(folder)], check=False)

    def _handle_preferences(self) -> None:
        """Handle preferences request."""
        def on_save(config):
            self._update_state()

        show_config_dialog(self._root, on_save)

    def _handle_quit(self) -> None:
        """Handle quit request."""
        # Confirm if download or transcription is in progress
        if self._download_manager.is_downloading:
            try:
                from tkinter import messagebox
                result = messagebox.askyesno(
                    "Download in Progress",
                    "Stop download and quit?\n\n"
                    "Your progress will be saved and you can resume later."
                )
                if not result:
                    return
            except Exception:
                pass  # Continue with quit if dialog fails
        elif self._transcription_manager.is_transcribing:
            try:
                from tkinter import messagebox
                result = messagebox.askyesno(
                    "Transcription in Progress",
                    "Stop transcription and quit?\n\n"
                    "Your progress will be saved and you can resume later."
                )
                if not result:
                    return
            except Exception:
                pass  # Continue with quit if dialog fails

        if self._root:
            self._root.quit()

    # Progress helpers
    _progress_dialog = None

    def _show_scan_progress(self) -> None:
        """Show scanning progress dialog."""
        self._progress_dialog = show_progress(
            self._root,
            "Scanning...",
            "Scanning Google Drive and Photos..."
        )

    def _hide_scan_progress(self) -> None:
        """Hide scanning progress dialog."""
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None


# Singleton instance
_app: Optional[GoogleMediaBackupApp] = None


def get_app() -> GoogleMediaBackupApp:
    """Get the global application instance."""
    global _app
    if _app is None:
        _app = GoogleMediaBackupApp()
    return _app
