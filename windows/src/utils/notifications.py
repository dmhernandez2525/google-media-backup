"""
Desktop notification utilities for Google Media Backup.
Uses plyer for cross-platform notifications on Windows.
"""

from typing import Optional
from .logger import get_logger

logger = get_logger()

# Try to import plyer for notifications
try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    logger.warning("plyer not installed, notifications will be disabled")


def show_notification(
    title: str,
    message: str,
    timeout: int = 10,
    app_name: str = "Google Media Backup"
) -> None:
    """
    Show a desktop notification.

    Args:
        title: Notification title
        message: Notification message
        timeout: How long to show (seconds)
        app_name: Application name
    """
    if not NOTIFICATIONS_AVAILABLE:
        logger.debug(f"Notification (disabled): {title} - {message}")
        return

    try:
        notification.notify(
            title=title,
            message=message,
            app_name=app_name,
            timeout=timeout
        )
        logger.debug(f"Notification shown: {title}")
    except Exception as e:
        logger.warning(f"Failed to show notification: {e}")


def notify_download_started(count: int) -> None:
    """Notify that downloads have started."""
    show_notification(
        title="Download Started",
        message=f"Downloading {count} file(s) from Google Drive and Photos..."
    )


def notify_download_complete(downloaded: int, skipped: int = 0, errors: int = 0) -> None:
    """Notify that downloads are complete."""
    parts = [f"{downloaded} downloaded"]
    if skipped > 0:
        parts.append(f"{skipped} skipped")
    if errors > 0:
        parts.append(f"{errors} errors")
    message = ", ".join(parts)
    show_notification(
        title="Download Complete",
        message=message
    )


def notify_download_error(filename: str, error: str) -> None:
    """Notify of a download error."""
    show_notification(
        title="Download Error",
        message=f"Failed to download {filename}: {error}"
    )


def notify_transcription_started(count: int) -> None:
    """Notify that transcription has started."""
    show_notification(
        title="Transcription Started",
        message="Processing videos..."
    )


def notify_transcription_file_complete(filename: str) -> None:
    """Notify that a single transcription is complete."""
    show_notification(
        title="Transcription Complete",
        message=f"Finished transcribing: {filename}"
    )


def notify_transcription_batch_complete(completed: int, failed: int = 0) -> None:
    """Notify that batch transcription is complete."""
    show_notification(
        title="Transcription Complete",
        message=f"{completed} transcribed, {failed} failed"
    )


def notify_transcription_error(filename: str, error: str) -> None:
    """Notify of a transcription error."""
    show_notification(
        title="Transcription Error",
        message=f"Failed to transcribe {filename}: {error}"
    )


def notify_sign_in_required() -> None:
    """Notify that sign-in is required."""
    show_notification(
        title="Sign In Required",
        message="Please sign in to your Google account to continue."
    )


def notify_signed_in() -> None:
    """Notify of successful sign-in."""
    show_notification(
        title="Sign In Successful",
        message="Ready to download from Google Drive and Photos."
    )


def notify_download_stopped() -> None:
    """Notify that downloads have been stopped."""
    show_notification(
        title="Download Stopped",
        message="Download has been stopped."
    )


def notify_transcription_stopped() -> None:
    """Notify that transcription has been stopped."""
    show_notification(
        title="Transcription Stopped",
        message="Transcription has been stopped."
    )
