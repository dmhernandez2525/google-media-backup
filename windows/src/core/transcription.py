"""
Transcription manager for video files using faster-whisper.
Handles audio extraction, model management, and transcript generation.
"""

import os
import subprocess
import shutil
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, List

from utils.config import get_config_manager, TranscriptionState
from utils.paths import Paths
from utils.logger import get_logger
from utils.notifications import (
    notify_transcription_started,
    notify_transcription_file_complete,
    notify_transcription_batch_complete,
    notify_transcription_error
)

logger = get_logger()


# Available Whisper models
WHISPER_MODELS = {
    "tiny": "tiny",
    "base": "base",
    "small": "small",
    "medium": "medium",
    "large": "large-v3",
}


class TranscriptionManager:
    """Manages video transcription using faster-whisper."""

    @staticmethod
    def is_ffmpeg_available() -> bool:
        """Check if ffmpeg is installed and available."""
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def is_transcription_ready() -> tuple:
        """
        Check if transcription is ready.

        Returns:
            Tuple of (is_ready: bool, status_message: str)
        """
        if not shutil.which("ffmpeg"):
            return False, "FFmpeg not installed"

        try:
            from faster_whisper import WhisperModel
            return True, "Ready"
        except ImportError:
            return False, "faster-whisper not installed"

    def __init__(self):
        self._model = None
        self._model_name: Optional[str] = None
        self._is_transcribing = False
        self._should_stop = False
        self._current_file: Optional[str] = None
        self._transcription_thread: Optional[threading.Thread] = None

        # Callbacks
        self._on_progress: Optional[Callable[[str, float], None]] = None
        self._on_complete: Optional[Callable[[str, str], None]] = None
        self._on_error: Optional[Callable[[str, str], None]] = None

    @property
    def is_transcribing(self) -> bool:
        """Check if transcription is in progress."""
        return self._is_transcribing

    @property
    def current_file(self) -> Optional[str]:
        """Get the name of the file currently being transcribed."""
        return self._current_file

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Set callback for transcription progress updates."""
        self._on_progress = callback

    def set_complete_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for when a transcription completes."""
        self._on_complete = callback

    def set_error_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for transcription errors."""
        self._on_error = callback

    def _load_model(self, model_name: str = "small") -> bool:
        """Load the Whisper model."""
        if self._model is not None and self._model_name == model_name:
            return True

        try:
            from faster_whisper import WhisperModel

            cache_dir = Paths.get_cache_dir()

            logger.info(f"Loading Whisper model: {model_name}")

            # Use CPU by default, CUDA if available
            device = "cpu"
            compute_type = "int8"

            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    compute_type = "float16"
                    logger.info("Using CUDA for transcription")
            except ImportError:
                pass

            self._model = WhisperModel(
                WHISPER_MODELS.get(model_name, model_name),
                device=device,
                compute_type=compute_type,
                download_root=str(cache_dir)
            )
            self._model_name = model_name

            logger.info(f"Loaded Whisper model: {model_name}")
            return True

        except ImportError:
            logger.error("faster-whisper not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return False

    def _extract_audio(self, video_path: Path, audio_path: Path) -> bool:
        """Extract audio from video using ffmpeg."""
        if not shutil.which("ffmpeg"):
            logger.error("ffmpeg not found in PATH")
            return False

        try:
            # Extract audio as 16kHz mono WAV
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-vn",  # No video
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-y",  # Overwrite
                str(audio_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg error: {result.stderr}")
                return False

            return audio_path.exists()

        except subprocess.TimeoutExpired:
            logger.error("Audio extraction timed out")
            return False
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            return False

    def transcribe_video(
        self,
        video_path: Path,
        output_format: str = "txt",
        language: str = "en"
    ) -> Optional[str]:
        """
        Transcribe a single video file.

        Args:
            video_path: Path to the video file
            output_format: Output format (txt, srt, vtt, both)
            language: Language code or "auto" for auto-detect

        Returns:
            Path to the transcript file, or None if failed
        """
        config_manager = get_config_manager()
        config = config_manager.get_config()

        # Load model if needed
        if not self._load_model(config.transcription_model):
            return None

        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"Video file not found: {video_path}")
            return None

        # Check if transcript already exists
        txt_path = video_path.with_suffix(".txt")
        srt_path = video_path.with_suffix(".srt")
        vtt_path = video_path.with_suffix(".vtt")

        if txt_path.exists():
            logger.info(f"Transcript already exists: {txt_path}")
            return str(txt_path)
        if srt_path.exists():
            logger.info(f"Transcript already exists: {srt_path}")
            return str(srt_path)
        if vtt_path.exists():
            logger.info(f"Transcript already exists: {vtt_path}")
            return str(vtt_path)

        # Create audio temp file
        audio_path = video_path.with_suffix(".wav")

        try:
            # Extract audio
            logger.info(f"Extracting audio from: {video_path.name}")
            if not self._extract_audio(video_path, audio_path):
                return None

            # Transcribe
            logger.info(f"Transcribing: {video_path.name}")

            # Handle auto language detection
            transcribe_language = None if language == "auto" else language

            segments, info = self._model.transcribe(
                str(audio_path),
                language=transcribe_language,
                beam_size=5,
                vad_filter=True
            )

            # Collect segments
            all_segments = list(segments)

            # Generate output based on format
            if output_format == "srt":
                transcript_path = video_path.with_suffix(".srt")
                self._write_srt(all_segments, transcript_path)
            elif output_format == "vtt":
                transcript_path = video_path.with_suffix(".vtt")
                self._write_vtt(all_segments, transcript_path)
            elif output_format == "both":
                # Create both txt and srt files
                txt_path = video_path.with_suffix(".txt")
                srt_path = video_path.with_suffix(".srt")
                self._write_txt(all_segments, txt_path)
                self._write_srt(all_segments, srt_path)
                transcript_path = txt_path  # Return txt path as primary
                logger.info(f"Transcript saved: {txt_path} and {srt_path}")
            else:
                transcript_path = video_path.with_suffix(".txt")
                self._write_txt(all_segments, transcript_path)

            if output_format != "both":
                logger.info(f"Transcript saved: {transcript_path}")
            return str(transcript_path)

        finally:
            # Cleanup audio file
            if audio_path.exists():
                try:
                    audio_path.unlink()
                except Exception:
                    pass

    def _write_txt(self, segments, output_path: Path) -> None:
        """Write transcript as plain text."""
        with open(output_path, "w", encoding="utf-8") as f:
            for segment in segments:
                f.write(segment.text.strip() + "\n")

    def _write_srt(self, segments, output_path: Path) -> None:
        """Write transcript as SRT subtitles."""
        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start = self._format_timestamp_srt(segment.start)
                end = self._format_timestamp_srt(segment.end)
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{segment.text.strip()}\n\n")

    def _write_vtt(self, segments, output_path: Path) -> None:
        """Write transcript as WebVTT subtitles."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for segment in segments:
                start = self._format_timestamp_vtt(segment.start)
                end = self._format_timestamp_vtt(segment.end)
                f.write(f"{start} --> {end}\n")
                f.write(f"{segment.text.strip()}\n\n")

    def _format_timestamp_srt(self, seconds: float) -> str:
        """Format timestamp for SRT (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_timestamp_vtt(self, seconds: float) -> str:
        """Format timestamp for VTT (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def transcribe_all_pending(self) -> None:
        """Transcribe all pending videos in background thread."""
        if self._is_transcribing:
            logger.warning("Transcription already in progress")
            return

        self._is_transcribing = True
        self._should_stop = False

        self._transcription_thread = threading.Thread(
            target=self._transcription_worker,
            daemon=True
        )
        self._transcription_thread.start()

    def stop_transcription(self) -> None:
        """Stop the current transcription."""
        if not self._is_transcribing:
            return

        self._should_stop = True

        if self._transcription_thread and self._transcription_thread.is_alive():
            self._transcription_thread.join(timeout=5.0)

        self._is_transcribing = False
        logger.info("Transcription stopped")

    def reset(self) -> None:
        """Reset state for new operations."""
        self._is_transcribing = False
        self._should_stop = False
        self._current_file = None

    def _transcription_worker(self) -> None:
        """Worker thread for transcribing videos."""
        config_manager = get_config_manager()
        config = config_manager.get_config()

        # Get pending videos
        pending_videos = self.get_pending_videos()

        if not pending_videos:
            logger.info("No pending videos to transcribe")
            self._is_transcribing = False
            return

        notify_transcription_started(len(pending_videos))
        completed_count = 0
        failed_count = 0

        for video_path in pending_videos:
            if self._should_stop:
                break

            self._current_file = Path(video_path).name

            if self._on_progress:
                self._on_progress(self._current_file, 0.0)

            # Create state entry
            state = TranscriptionState(video_path=video_path, status="transcribing")
            config_manager.update_transcription(state)

            # Update FileState transcription_status
            self._update_file_transcription_status(config_manager, video_path, "transcribing")

            try:
                transcript_path = self.transcribe_video(
                    Path(video_path),
                    output_format=config.transcription_output_format,
                    language=config.transcription_language
                )

                if transcript_path:
                    state.status = "complete"
                    state.transcript_path = transcript_path
                    state.transcribed_at = datetime.now().isoformat()
                    completed_count += 1

                    # Update FileState transcription_status
                    self._update_file_transcription_status(
                        config_manager, video_path, "complete",
                        transcribed_at=state.transcribed_at
                    )

                    if self._on_complete:
                        self._on_complete(video_path, transcript_path)

                    notify_transcription_file_complete(Path(video_path).name)
                else:
                    state.status = "error"
                    state.error_message = "Transcription failed"
                    failed_count += 1

                    # Update FileState transcription_status
                    self._update_file_transcription_status(config_manager, video_path, "error")

                    if self._on_error:
                        self._on_error(video_path, "Transcription failed")

            except Exception as e:
                logger.error(f"Error transcribing {video_path}: {e}")
                state.status = "error"
                state.error_message = str(e)
                failed_count += 1

                # Update FileState transcription_status
                self._update_file_transcription_status(config_manager, video_path, "error")

                if self._on_error:
                    self._on_error(video_path, str(e))

                notify_transcription_error(Path(video_path).name, str(e))

            config_manager.update_transcription(state)

        self._current_file = None
        self._is_transcribing = False

        logger.info(f"Transcription complete: {completed_count}/{len(pending_videos)}")

        # Show batch completion notification
        notify_transcription_batch_complete(completed_count, failed_count)

    def _update_file_transcription_status(
        self,
        config_manager,
        video_path: str,
        status: str,
        transcribed_at: Optional[str] = None
    ) -> None:
        """Update the FileState's transcription status."""
        # Find the file in drive or photos state
        for file_state in config_manager.get_drive_state().values():
            if file_state.local_path == video_path:
                file_state.transcription_status = status
                if transcribed_at:
                    file_state.transcribed_at = transcribed_at
                config_manager.update_drive_file(file_state)
                return

        for file_state in config_manager.get_photos_state().values():
            if file_state.local_path == video_path:
                file_state.transcription_status = status
                if transcribed_at:
                    file_state.transcribed_at = transcribed_at
                config_manager.update_photos_file(file_state)
                return

    def get_pending_videos(self) -> List[str]:
        """Get list of videos pending transcription."""
        config_manager = get_config_manager()
        transcription_state = config_manager.get_transcription_state()
        pending = []

        # Get all completed video downloads
        for file_state in config_manager.get_drive_state().values():
            if file_state.status == "complete" and file_state.mime_type.startswith("video/"):
                if file_state.local_path:
                    # Check if not already transcribed
                    trans = transcription_state.get(file_state.local_path)
                    if not trans or trans.status == "pending":
                        pending.append(file_state.local_path)

        for file_state in config_manager.get_photos_state().values():
            if file_state.status == "complete" and file_state.mime_type.startswith("video/"):
                if file_state.local_path:
                    trans = transcription_state.get(file_state.local_path)
                    if not trans or trans.status == "pending":
                        pending.append(file_state.local_path)

        return pending

    def get_pending_count(self) -> int:
        """Get count of videos pending transcription."""
        return len(self.get_pending_videos())


# Singleton instance
_transcription_manager: Optional[TranscriptionManager] = None


def get_transcription_manager() -> TranscriptionManager:
    """Get the global TranscriptionManager instance."""
    global _transcription_manager
    if _transcription_manager is None:
        _transcription_manager = TranscriptionManager()
    return _transcription_manager
