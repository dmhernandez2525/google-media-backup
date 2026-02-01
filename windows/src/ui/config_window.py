"""
Configuration/preferences window for Google Media Backup.
"""

import os
from pathlib import Path
from typing import Optional, Callable
from tkinter import filedialog

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk
    CTK_AVAILABLE = False

from utils.config import get_config_manager, AppConfig
from utils.paths import Paths
from utils.logger import get_logger

logger = get_logger()


class ConfigWindow:
    """Preferences/settings window."""

    def __init__(self, parent=None):
        self.parent = parent
        self.window: Optional[ctk.CTkToplevel] = None
        self._on_save: Optional[Callable[[AppConfig], None]] = None

    def show(self, on_save: Optional[Callable[[AppConfig], None]] = None) -> None:
        """Show the configuration window."""
        self._on_save = on_save

        if self.window is not None:
            self.window.deiconify()
            self.window.lift()
            return

        self._create_window()

    def _create_window(self) -> None:
        """Create the configuration window."""
        config_manager = get_config_manager()
        config = config_manager.get_config()

        if CTK_AVAILABLE:
            if self.parent:
                self.window = ctk.CTkToplevel(self.parent)
            else:
                self.window = ctk.CTkToplevel()
        else:
            if self.parent:
                self.window = tk.Toplevel(self.parent)
            else:
                self.window = tk.Tk()

        self.window.title("Preferences")
        self.window.geometry("500x720")
        self.window.resizable(False, False)

        # Center on screen
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 500) // 2
        y = (self.window.winfo_screenheight() - 720) // 2
        self.window.geometry(f"500x720+{x}+{y}")

        if not CTK_AVAILABLE:
            return

        # Main frame with padding
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="Preferences",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(0, 20), anchor="w")

        # Google Account Section
        account_label = ctk.CTkLabel(
            main_frame,
            text="Google Account:",
            font=ctk.CTkFont(weight="bold")
        )
        account_label.pack(anchor="w")

        account_frame = ctk.CTkFrame(main_frame)
        account_frame.pack(fill="x", pady=(5, 15))

        # Check auth status
        from core.google_auth import get_auth_manager
        auth_manager = get_auth_manager()
        is_authenticated = auth_manager.is_authenticated

        if is_authenticated:
            status_text = "Connected to Google"
            status_color = "#4CAF50"
        else:
            status_text = "Not signed in"
            status_color = "#9E9E9E"

        status_label = ctk.CTkLabel(
            account_frame,
            text=status_text,
            text_color=status_color
        )
        status_label.pack(side="left", padx=15, pady=10)

        if is_authenticated:
            sign_out_btn = ctk.CTkButton(
                account_frame,
                text="Sign Out",
                width=80,
                fg_color="#F44336",
                hover_color="#D32F2F",
                command=self._sign_out
            )
            sign_out_btn.pack(side="right", padx=15, pady=10)
        else:
            sign_in_btn = ctk.CTkButton(
                account_frame,
                text="Sign In",
                width=80,
                command=self._sign_in
            )
            sign_in_btn.pack(side="right", padx=15, pady=10)

        # Download Path
        path_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        path_frame.pack(fill="x", pady=10)

        path_label = ctk.CTkLabel(path_frame, text="Download Location:")
        path_label.pack(anchor="w")

        path_entry_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        path_entry_frame.pack(fill="x", pady=5)

        self.path_var = ctk.StringVar(value=config.download_path)
        path_entry = ctk.CTkEntry(path_entry_frame, textvariable=self.path_var, width=350)
        path_entry.pack(side="left", fill="x", expand=True)

        browse_btn = ctk.CTkButton(
            path_entry_frame,
            text="Browse",
            width=80,
            command=self._browse_folder
        )
        browse_btn.pack(side="right", padx=(10, 0))

        # Content Types section
        content_label = ctk.CTkLabel(
            main_frame,
            text="Content to Download:",
            font=ctk.CTkFont(weight="bold")
        )
        content_label.pack(pady=(20, 10), anchor="w")

        self.videos_var = ctk.BooleanVar(value=config.download_videos)
        videos_cb = ctk.CTkCheckBox(main_frame, text="Videos", variable=self.videos_var)
        videos_cb.pack(anchor="w", pady=2)

        self.documents_var = ctk.BooleanVar(value=config.download_documents)
        documents_cb = ctk.CTkCheckBox(main_frame, text="Documents", variable=self.documents_var)
        documents_cb.pack(anchor="w", pady=2)

        self.photos_var = ctk.BooleanVar(value=config.download_photos)
        photos_cb = ctk.CTkCheckBox(main_frame, text="Google Photos Videos", variable=self.photos_var)
        photos_cb.pack(anchor="w", pady=2)

        # Auto-download
        self.auto_download_var = ctk.BooleanVar(value=config.auto_download)
        auto_download_cb = ctk.CTkCheckBox(
            main_frame,
            text="Auto-download on startup",
            variable=self.auto_download_var
        )
        auto_download_cb.pack(anchor="w", pady=(15, 2))

        # Transcription section
        trans_label = ctk.CTkLabel(
            main_frame,
            text="Transcription:",
            font=ctk.CTkFont(weight="bold")
        )
        trans_label.pack(pady=(20, 10), anchor="w")

        self.auto_transcribe_var = ctk.BooleanVar(value=config.auto_transcribe)
        auto_trans_cb = ctk.CTkCheckBox(
            main_frame,
            text="Auto-transcribe videos after download",
            variable=self.auto_transcribe_var
        )
        auto_trans_cb.pack(anchor="w", pady=2)

        # Model selection
        model_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        model_frame.pack(fill="x", pady=10)

        model_label = ctk.CTkLabel(model_frame, text="Whisper Model:")
        model_label.pack(side="left")

        self.model_var = ctk.StringVar(value=config.transcription_model)
        model_menu = ctk.CTkOptionMenu(
            model_frame,
            values=["tiny", "base", "small", "medium"],
            variable=self.model_var
        )
        model_menu.pack(side="left", padx=10)

        model_hint = ctk.CTkLabel(
            main_frame,
            text="Larger models are more accurate but slower",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        model_hint.pack(anchor="w")

        # Whisper status
        from core.transcription import TranscriptionManager
        is_ready, status_msg = TranscriptionManager.is_transcription_ready()

        whisper_status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        whisper_status_frame.pack(fill="x", pady=5)

        whisper_status_label = ctk.CTkLabel(
            whisper_status_frame,
            text="Status: ",
            font=ctk.CTkFont(size=11)
        )
        whisper_status_label.pack(side="left")

        if is_ready:
            status_color = "#4CAF50"
        else:
            status_color = "#FF9800"

        whisper_status_value = ctk.CTkLabel(
            whisper_status_frame,
            text=status_msg,
            font=ctk.CTkFont(size=11),
            text_color=status_color
        )
        whisper_status_value.pack(side="left")

        # Output format
        format_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        format_frame.pack(fill="x", pady=10)

        format_label = ctk.CTkLabel(format_frame, text="Output Format:")
        format_label.pack(side="left")

        self.format_var = ctk.StringVar(value=config.transcription_output_format)
        format_menu = ctk.CTkOptionMenu(
            format_frame,
            values=["txt", "srt", "vtt", "both"],
            variable=self.format_var
        )
        format_menu.pack(side="left", padx=10)

        format_hint = ctk.CTkLabel(
            main_frame,
            text="'both' creates both .txt and .srt files",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        format_hint.pack(anchor="w")

        # Language selection
        lang_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        lang_frame.pack(fill="x", pady=10)

        lang_label = ctk.CTkLabel(lang_frame, text="Language:")
        lang_label.pack(side="left")

        self.language_var = ctk.StringVar(value=config.transcription_language)
        lang_menu = ctk.CTkOptionMenu(
            lang_frame,
            values=["en", "auto"],
            variable=self.language_var
        )
        lang_menu.pack(side="left", padx=10)

        lang_hint = ctk.CTkLabel(
            main_frame,
            text="'auto' will detect the language automatically",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        lang_hint.pack(anchor="w")

        # Spacer
        spacer = ctk.CTkFrame(main_frame, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=10)

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._save
        )
        save_btn.pack(side="right", padx=5)

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._close,
            fg_color="transparent",
            border_width=1
        )
        cancel_btn.pack(side="right", padx=5)

    def _sign_in(self) -> None:
        """Handle sign in from preferences."""
        from ui.auth_window import show_auth_dialog

        def on_complete(success: bool, message: str):
            # Refresh the preferences window
            if self.window:
                self._close()
                self.show(self._on_save)

        show_auth_dialog(self.window, on_complete)

    def _sign_out(self) -> None:
        """Handle sign out from preferences."""
        from core.google_auth import get_auth_manager
        auth_manager = get_auth_manager()
        auth_manager.sign_out()

        # Refresh the preferences window
        if self.window:
            self._close()
            self.show(self._on_save)

    def _browse_folder(self) -> None:
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(
            title="Select Download Location",
            initialdir=self.path_var.get()
        )
        if folder:
            self.path_var.set(folder)

    def _save(self) -> None:
        """Save configuration."""
        config_manager = get_config_manager()

        new_config = AppConfig(
            download_path=self.path_var.get(),
            auto_download=self.auto_download_var.get(),
            auto_transcribe=self.auto_transcribe_var.get(),
            transcription_model=self.model_var.get(),
            transcription_output_format=self.format_var.get(),
            transcription_language=self.language_var.get(),
            download_videos=self.videos_var.get(),
            download_documents=self.documents_var.get(),
            download_photos=self.photos_var.get()
        )

        config_manager.save_config(new_config)
        logger.info("Configuration saved")

        if self._on_save:
            self._on_save(new_config)

        self._close()

    def _close(self) -> None:
        """Close the window."""
        if self.window:
            self.window.destroy()
            self.window = None


def show_config_dialog(parent=None, on_save: Optional[Callable[[AppConfig], None]] = None) -> ConfigWindow:
    """Show the configuration dialog."""
    window = ConfigWindow(parent)
    window.show(on_save)
    return window
