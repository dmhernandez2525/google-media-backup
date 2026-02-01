"""
Windows path utilities for Google Media Backup.
Follows Windows conventions for config and data storage.
"""

import os
from pathlib import Path
from typing import Optional


class Paths:
    """Centralized path management for the application."""

    APP_NAME = "GoogleMediaBackup"

    @classmethod
    def get_appdata_dir(cls) -> Path:
        """Get the roaming AppData directory for config storage."""
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = Path.home() / "AppData" / "Roaming"
        return Path(appdata) / cls.APP_NAME

    @classmethod
    def get_localappdata_dir(cls) -> Path:
        """Get the local AppData directory for cache storage."""
        localappdata = os.environ.get("LOCALAPPDATA")
        if not localappdata:
            localappdata = Path.home() / "AppData" / "Local"
        return Path(localappdata) / cls.APP_NAME

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the configuration directory. Creates it if it doesn't exist."""
        config_dir = cls.get_appdata_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @classmethod
    def get_state_dir(cls) -> Path:
        """Get the state directory for download/transcription state."""
        state_dir = cls.get_config_dir() / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    @classmethod
    def get_cache_dir(cls) -> Path:
        """Get the cache directory for Whisper models."""
        cache_dir = cls.get_localappdata_dir() / "whisper"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @classmethod
    def get_default_download_dir(cls) -> Path:
        """Get the default download directory on Desktop."""
        desktop = Path.home() / "Desktop"
        download_dir = desktop / "Google Media Backup"
        return download_dir

    @classmethod
    def get_videos_dir(cls, download_dir: Optional[Path] = None) -> Path:
        """Get the Videos subdirectory."""
        base = download_dir or cls.get_default_download_dir()
        videos_dir = base / "Videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        return videos_dir

    @classmethod
    def get_drive_videos_dir(cls, download_dir: Optional[Path] = None) -> Path:
        """Get the Videos/Drive subdirectory."""
        videos_dir = cls.get_videos_dir(download_dir)
        drive_dir = videos_dir / "Drive"
        drive_dir.mkdir(parents=True, exist_ok=True)
        return drive_dir

    @classmethod
    def get_photos_videos_dir(cls, download_dir: Optional[Path] = None) -> Path:
        """Get the Videos/Photos subdirectory."""
        videos_dir = cls.get_videos_dir(download_dir)
        photos_dir = videos_dir / "Photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        return photos_dir

    @classmethod
    def get_documents_dir(cls, download_dir: Optional[Path] = None) -> Path:
        """Get the Documents subdirectory."""
        base = download_dir or cls.get_default_download_dir()
        docs_dir = base / "Documents"
        docs_dir.mkdir(parents=True, exist_ok=True)
        return docs_dir

    # Config file paths
    @classmethod
    def get_config_file(cls) -> Path:
        """Get the main config.json path."""
        return cls.get_config_dir() / "config.json"

    @classmethod
    def get_credentials_file(cls) -> Path:
        """Get the Google OAuth credentials.json path."""
        return cls.get_config_dir() / "credentials.json"

    @classmethod
    def get_token_file(cls) -> Path:
        """Get the OAuth token.json path."""
        return cls.get_config_dir() / "token.json"

    @classmethod
    def get_log_file(cls) -> Path:
        """Get the application log file path."""
        return cls.get_config_dir() / "app.log"

    @classmethod
    def get_setup_complete_file(cls) -> Path:
        """Get the setup completion flag file path."""
        return cls.get_config_dir() / "setup_complete.json"

    # State file paths
    @classmethod
    def get_drive_state_file(cls) -> Path:
        """Get the Drive state file path."""
        return cls.get_state_dir() / "drive_state.json"

    @classmethod
    def get_photos_state_file(cls) -> Path:
        """Get the Photos state file path."""
        return cls.get_state_dir() / "photos_state.json"

    @classmethod
    def get_transcription_state_file(cls) -> Path:
        """Get the transcription state file path."""
        return cls.get_state_dir() / "transcription_state.json"

    @classmethod
    def ensure_all_directories(cls) -> None:
        """Create all necessary directories."""
        cls.get_config_dir()
        cls.get_state_dir()
        cls.get_cache_dir()
        # Don't create download directories until user starts downloading
