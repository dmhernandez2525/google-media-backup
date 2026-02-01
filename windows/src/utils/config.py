"""
Configuration management for Google Media Backup.
Handles app settings and download/transcription state persistence.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

from .paths import Paths
from .logger import get_logger


logger = get_logger()


@dataclass
class AppConfig:
    """Application configuration settings."""
    download_path: str = ""
    auto_download: bool = False
    auto_transcribe: bool = True
    transcription_model: str = "small"
    transcription_output_format: str = "txt"  # txt, srt, vtt, both (txt + srt)
    transcription_language: str = "en"  # Language code or "auto" for auto-detect
    download_videos: bool = True
    download_documents: bool = True
    download_photos: bool = True
    max_concurrent_downloads: int = 3  # Match macOS default
    exclude_patterns: List[str] = field(default_factory=lambda: ["*.tmp", "*.part"])

    def __post_init__(self):
        if not self.download_path:
            self.download_path = str(Paths.get_default_download_dir())


@dataclass
class FileState:
    """State of a single file (for download/transcription tracking)."""
    id: str
    name: str
    source: str  # 'drive' or 'photos'
    mime_type: str = ""
    size: int = 0
    status: str = "pending"  # pending, downloading, complete, error
    downloaded_at: Optional[str] = None
    local_path: Optional[str] = None
    error_message: Optional[str] = None
    modified_time: Optional[str] = None
    transcription_status: str = "pending"  # pending, transcribing, complete, error, n/a
    transcribed_at: Optional[str] = None

    @property
    def is_video(self) -> bool:
        """Check if this is a video file."""
        video_types = ["video/mp4", "video/quicktime", "video/x-msvideo",
                       "video/webm", "video/3gpp", "video/mpeg", "video/x-matroska"]
        return self.mime_type in video_types or self.mime_type.startswith("video/")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileState":
        return cls(**data)


@dataclass
class TranscriptionState:
    """State of transcription for a video file."""
    video_path: str
    status: str = "pending"  # pending, transcribing, complete, error
    transcript_path: Optional[str] = None
    transcribed_at: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptionState":
        return cls(**data)


@dataclass
class SyncState:
    """State of a sync source (Drive or Photos)."""
    last_sync_time: Optional[str] = None
    total_files: int = 0
    completed_files: int = 0
    error_files: int = 0


@dataclass
class DownloadStats:
    """Statistics about download progress."""
    total: int = 0
    downloaded: int = 0
    pending: int = 0
    errors: int = 0
    videos_for_transcription: int = 0


class ConfigManager:
    """Manages application configuration and state."""

    def __init__(self):
        self._config: Optional[AppConfig] = None
        self._drive_state: Dict[str, FileState] = {}
        self._photos_state: Dict[str, FileState] = {}
        self._transcription_state: Dict[str, TranscriptionState] = {}
        self._drive_sync_state: Optional[SyncState] = None
        self._photos_sync_state: Optional[SyncState] = None

    def get_config(self) -> AppConfig:
        """Get the current configuration, loading from disk if needed."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def save_config(self, config: Optional[AppConfig] = None) -> None:
        """Save configuration to disk."""
        if config is not None:
            self._config = config

        if self._config is None:
            return

        config_file = Paths.get_config_file()
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(asdict(self._config), f, indent=2)
            logger.debug(f"Saved config to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def _load_config(self) -> AppConfig:
        """Load configuration from disk."""
        config_file = Paths.get_config_file()

        if not config_file.exists():
            logger.info("No config file found, using defaults")
            return AppConfig()

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Handle missing fields gracefully
            return AppConfig(**{k: v for k, v in data.items() if hasattr(AppConfig, k)})
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return AppConfig()

    # Drive state management
    def get_drive_state(self) -> Dict[str, FileState]:
        """Get Drive file states, loading from disk if needed."""
        if not self._drive_state:
            self._drive_state = self._load_state(Paths.get_drive_state_file())
        return self._drive_state

    def save_drive_state(self) -> None:
        """Save Drive state to disk."""
        self._save_state(self._drive_state, Paths.get_drive_state_file())

    def update_drive_file(self, file_state: FileState) -> None:
        """Update a single Drive file state."""
        self._drive_state[file_state.id] = file_state
        self.save_drive_state()

    def update_drive_sync_time(self) -> None:
        """Update the last sync time for Drive."""
        if self._drive_sync_state is None:
            self._drive_sync_state = SyncState()
        self._drive_sync_state.last_sync_time = datetime.now().isoformat()
        self._update_sync_counts("drive")
        self.save_drive_state()

    def get_drive_sync_state(self) -> SyncState:
        """Get the Drive sync state."""
        if self._drive_sync_state is None:
            self._drive_sync_state = SyncState()
        return self._drive_sync_state

    # Photos state management
    def get_photos_state(self) -> Dict[str, FileState]:
        """Get Photos file states, loading from disk if needed."""
        if not self._photos_state:
            self._photos_state = self._load_state(Paths.get_photos_state_file())
        return self._photos_state

    def save_photos_state(self) -> None:
        """Save Photos state to disk."""
        self._save_state(self._photos_state, Paths.get_photos_state_file())

    def update_photos_file(self, file_state: FileState) -> None:
        """Update a single Photos file state."""
        self._photos_state[file_state.id] = file_state
        self.save_photos_state()

    def update_photos_sync_time(self) -> None:
        """Update the last sync time for Photos."""
        if self._photos_sync_state is None:
            self._photos_sync_state = SyncState()
        self._photos_sync_state.last_sync_time = datetime.now().isoformat()
        self._update_sync_counts("photos")
        self.save_photos_state()

    def get_photos_sync_state(self) -> SyncState:
        """Get the Photos sync state."""
        if self._photos_sync_state is None:
            self._photos_sync_state = SyncState()
        return self._photos_sync_state

    def _update_sync_counts(self, source: str) -> None:
        """Update sync counts for a source."""
        if source == "drive":
            state = self._drive_sync_state
            files = self._drive_state
        else:
            state = self._photos_sync_state
            files = self._photos_state

        if state is None:
            return

        state.total_files = len(files)
        state.completed_files = sum(1 for f in files.values() if f.status == "complete")
        state.error_files = sum(1 for f in files.values() if f.status == "error")

    # Transcription state management
    def get_transcription_state(self) -> Dict[str, TranscriptionState]:
        """Get transcription states, loading from disk if needed."""
        if not self._transcription_state:
            self._transcription_state = self._load_transcription_state()
        return self._transcription_state

    def save_transcription_state(self) -> None:
        """Save transcription state to disk."""
        state_file = Paths.get_transcription_state_file()
        try:
            data = {k: v.to_dict() for k, v in self._transcription_state.items()}
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save transcription state: {e}")

    def update_transcription(self, state: TranscriptionState) -> None:
        """Update a single transcription state."""
        self._transcription_state[state.video_path] = state
        self.save_transcription_state()

    def _load_transcription_state(self) -> Dict[str, TranscriptionState]:
        """Load transcription state from disk."""
        state_file = Paths.get_transcription_state_file()

        if not state_file.exists():
            return {}

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k: TranscriptionState.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to load transcription state: {e}")
            return {}

    def _load_state(self, state_file: Path) -> Dict[str, FileState]:
        """Load file states from disk."""
        if not state_file.exists():
            return {}

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k: FileState.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to load state from {state_file}: {e}")
            return {}

    def _save_state(self, state: Dict[str, FileState], state_file: Path) -> None:
        """Save file states to disk."""
        try:
            data = {k: v.to_dict() for k, v in state.items()}
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state to {state_file}: {e}")

    def get_download_stats(self) -> DownloadStats:
        """Calculate download statistics."""
        stats = DownloadStats()

        for state in list(self._drive_state.values()) + list(self._photos_state.values()):
            stats.total += 1
            if state.status == "complete":
                stats.downloaded += 1
                # Check if it's a video that needs transcription
                if state.is_video:
                    if state.transcription_status == "pending" or state.transcription_status == "n/a":
                        # Also check transcription state dict
                        if state.local_path:
                            trans_state = self._transcription_state.get(state.local_path)
                            if not trans_state or trans_state.status == "pending":
                                stats.videos_for_transcription += 1
                        else:
                            stats.videos_for_transcription += 1
            elif state.status == "pending":
                stats.pending += 1
            elif state.status == "error":
                stats.errors += 1

        return stats

    def get_all_files(self) -> List[FileState]:
        """Get all files from both Drive and Photos, sorted by download time."""
        all_files = list(self._drive_state.values()) + list(self._photos_state.values())
        return sorted(all_files, key=lambda f: f.downloaded_at or "", reverse=True)

    def get_videos_for_transcription(self) -> List[FileState]:
        """Get videos that need transcription."""
        videos = []
        for state in self.get_all_files():
            if (state.is_video and
                state.status == "complete" and
                state.transcription_status == "pending" and
                state.local_path):
                videos.append(state)
        return videos

    def clear_all_state(self) -> None:
        """Clear all download and transcription state."""
        self._drive_state = {}
        self._photos_state = {}
        self._transcription_state = {}
        self.save_drive_state()
        self.save_photos_state()
        self.save_transcription_state()
        logger.info("Cleared all state")


# Singleton instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
