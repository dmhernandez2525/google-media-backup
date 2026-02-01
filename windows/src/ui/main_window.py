"""
Main window for Google Media Backup.
Modern, clean interface with sidebar navigation.
"""

import os
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, Callable, List

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk
    CTK_AVAILABLE = False

from utils.logger import get_logger
from utils.config import FileState, DownloadStats

logger = get_logger()

# Color scheme
COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_sidebar": "#16213e",
    "bg_card": "#202040",
    "bg_card_hover": "#2a2a50",
    "accent": "#4361ee",
    "accent_hover": "#3651d4",
    "success": "#06d6a0",
    "warning": "#ffd166",
    "error": "#ef476f",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0b0",
    "text_muted": "#606070",
    "border": "#303050",
    "google_blue": "#4285f4",
    "google_green": "#34a853",
}


class MainWindow:
    """Main application window with modern UI."""

    def __init__(self):
        self.window: Optional[ctk.CTk] = None
        self._current_tab = "home"

        # Callbacks
        self._on_sign_in: Optional[Callable[[], None]] = None
        self._on_sign_out: Optional[Callable[[], None]] = None
        self._on_start_download: Optional[Callable[[], None]] = None
        self._on_stop_download: Optional[Callable[[], None]] = None
        self._on_pause_download: Optional[Callable[[], None]] = None
        self._on_resume_download: Optional[Callable[[], None]] = None
        self._on_scan: Optional[Callable[[], None]] = None
        self._on_transcribe: Optional[Callable[[], None]] = None
        self._on_stop_transcription: Optional[Callable[[], None]] = None
        self._on_open_folder: Optional[Callable[[], None]] = None
        self._on_preferences: Optional[Callable[[], None]] = None

        # State
        self._is_authenticated = False
        self._is_downloading = False
        self._is_paused = False
        self._is_transcribing = False
        self._stats = DownloadStats()

    def set_callbacks(
        self,
        on_sign_in: Optional[Callable[[], None]] = None,
        on_sign_out: Optional[Callable[[], None]] = None,
        on_start_download: Optional[Callable[[], None]] = None,
        on_stop_download: Optional[Callable[[], None]] = None,
        on_pause_download: Optional[Callable[[], None]] = None,
        on_resume_download: Optional[Callable[[], None]] = None,
        on_scan: Optional[Callable[[], None]] = None,
        on_transcribe: Optional[Callable[[], None]] = None,
        on_stop_transcription: Optional[Callable[[], None]] = None,
        on_open_folder: Optional[Callable[[], None]] = None,
        on_preferences: Optional[Callable[[], None]] = None
    ) -> None:
        """Set callback functions for UI actions."""
        self._on_sign_in = on_sign_in
        self._on_sign_out = on_sign_out
        self._on_start_download = on_start_download
        self._on_stop_download = on_stop_download
        self._on_pause_download = on_pause_download
        self._on_resume_download = on_resume_download
        self._on_scan = on_scan
        self._on_transcribe = on_transcribe
        self._on_stop_transcription = on_stop_transcription
        self._on_open_folder = on_open_folder
        self._on_preferences = on_preferences

    def show(self) -> None:
        """Show the main window."""
        if self.window is not None:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            return

        self._create_window()

    def hide(self) -> None:
        """Hide/minimize the main window."""
        if self.window:
            self.window.iconify()

    def close(self) -> None:
        """Close and destroy the window."""
        if self.window:
            self.window.quit()
            self.window = None

    def update_state(
        self,
        is_authenticated: Optional[bool] = None,
        is_downloading: Optional[bool] = None,
        is_paused: Optional[bool] = None,
        is_transcribing: Optional[bool] = None,
        stats: Optional[DownloadStats] = None
    ) -> None:
        """Update the UI state."""
        if is_authenticated is not None:
            self._is_authenticated = is_authenticated
        if is_downloading is not None:
            self._is_downloading = is_downloading
        if is_paused is not None:
            self._is_paused = is_paused
        if is_transcribing is not None:
            self._is_transcribing = is_transcribing
        if stats is not None:
            self._stats = stats

        if self.window:
            self.window.after(0, self._refresh_ui)

    def _create_window(self) -> None:
        """Create the main window."""
        if CTK_AVAILABLE:
            self._create_ctk_window()
        else:
            self._create_tk_window()

    def _create_ctk_window(self) -> None:
        """Create window using CustomTkinter with modern dark theme."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.window = ctk.CTk()
        self.window.title("Google Media Backup")
        self.window.geometry("1000x700")
        self.window.minsize(800, 550)
        self.window.configure(fg_color=COLORS["bg_dark"])

        # Center on screen
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 1000) // 2
        y = (self.window.winfo_screenheight() - 700) // 2
        self.window.geometry(f"1000x700+{x}+{y}")

        # Main container
        self.main_frame = ctk.CTkFrame(self.window, fg_color=COLORS["bg_dark"])
        self.main_frame.pack(fill="both", expand=True)

        # Sidebar
        self._create_sidebar()

        # Content area
        self.content_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_dark"],
            corner_radius=0
        )
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(0, 20), pady=20)

        # Show home tab by default
        self._show_home_tab()

    def _create_sidebar(self) -> None:
        """Create the sidebar navigation."""
        sidebar = ctk.CTkFrame(
            self.main_frame,
            width=220,
            fg_color=COLORS["bg_sidebar"],
            corner_radius=0
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # App logo/title area
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", pady=(30, 40), padx=20)

        # App icon (cloud symbol using text)
        icon_label = ctk.CTkLabel(
            logo_frame,
            text="☁",
            font=ctk.CTkFont(size=36),
            text_color=COLORS["google_blue"]
        )
        icon_label.pack()

        title = ctk.CTkLabel(
            logo_frame,
            text="Google Media\nBackup",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"],
            justify="center"
        )
        title.pack(pady=(10, 0))

        # Navigation buttons
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=15)

        self.nav_buttons = {}

        nav_items = [
            ("home", "🏠  Home"),
            ("downloads", "📥  Downloads"),
            ("transcriptions", "📝  Transcriptions"),
        ]

        for tab_id, label in nav_items:
            btn = ctk.CTkButton(
                nav_frame,
                text=label,
                command=lambda t=tab_id: self._switch_tab(t),
                width=190,
                height=45,
                font=ctk.CTkFont(size=14),
                fg_color=COLORS["accent"] if tab_id == "home" else "transparent",
                hover_color=COLORS["accent_hover"],
                anchor="w",
                corner_radius=10
            )
            btn.pack(pady=5)
            self.nav_buttons[tab_id] = btn

        # Spacer
        spacer = ctk.CTkFrame(sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Bottom section
        bottom_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=20, padx=15)

        # Settings button
        settings_btn = ctk.CTkButton(
            bottom_frame,
            text="⚙  Settings",
            command=self._on_preferences,
            width=190,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            hover_color=COLORS["bg_card"],
            anchor="w",
            corner_radius=10
        )
        settings_btn.pack(pady=5)

        # Open folder button
        folder_btn = ctk.CTkButton(
            bottom_frame,
            text="📁  Open Folder",
            command=self._on_open_folder,
            width=190,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            hover_color=COLORS["bg_card"],
            anchor="w",
            corner_radius=10
        )
        folder_btn.pack(pady=5)

    def _switch_tab(self, tab: str) -> None:
        """Switch to a different tab."""
        self._current_tab = tab

        # Update button styles
        for name, btn in self.nav_buttons.items():
            if name == tab:
                btn.configure(fg_color=COLORS["accent"])
            else:
                btn.configure(fg_color="transparent")

        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Show new tab
        if tab == "home":
            self._show_home_tab()
        elif tab == "downloads":
            self._show_downloads_tab()
        elif tab == "transcriptions":
            self._show_transcriptions_tab()

    def _show_home_tab(self) -> None:
        """Show the home tab content."""
        # Scrollable container
        scroll = ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color="transparent"
        )
        scroll.pack(fill="both", expand=True)

        # Header
        header_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        header = ctk.CTkLabel(
            header_frame,
            text="Dashboard",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        header.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Manage your Google Drive and Photos backups",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        )
        subtitle.pack(anchor="w", pady=(5, 0))

        # Connection status card
        status_card = ctk.CTkFrame(
            scroll,
            fg_color=COLORS["bg_card"],
            corner_radius=15
        )
        status_card.pack(fill="x", pady=(0, 20))

        status_inner = ctk.CTkFrame(status_card, fg_color="transparent")
        status_inner.pack(fill="x", padx=25, pady=25)

        # Status row
        status_row = ctk.CTkFrame(status_inner, fg_color="transparent")
        status_row.pack(fill="x")

        if self._is_authenticated:
            status_icon = "✓"
            status_text = "Connected to Google"
            status_color = COLORS["success"]
        else:
            status_icon = "○"
            status_text = "Not connected"
            status_color = COLORS["text_muted"]

        status_indicator = ctk.CTkLabel(
            status_row,
            text=status_icon,
            font=ctk.CTkFont(size=20),
            text_color=status_color
        )
        status_indicator.pack(side="left")

        status_label = ctk.CTkLabel(
            status_row,
            text=status_text,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=status_color
        )
        status_label.pack(side="left", padx=(10, 0))

        # Auth button
        if self._is_authenticated:
            auth_btn = ctk.CTkButton(
                status_row,
                text="Sign Out",
                command=self._on_sign_out,
                width=100,
                height=35,
                fg_color=COLORS["error"],
                hover_color="#d63d5c",
                corner_radius=8
            )
        else:
            auth_btn = ctk.CTkButton(
                status_row,
                text="Sign In with Google",
                command=self._on_sign_in,
                width=160,
                height=40,
                fg_color=COLORS["google_blue"],
                hover_color="#3574e3",
                corner_radius=8,
                font=ctk.CTkFont(size=14, weight="bold")
            )
        auth_btn.pack(side="right")

        # Statistics cards
        stats_label = ctk.CTkLabel(
            scroll,
            text="Statistics",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        stats_label.pack(anchor="w", pady=(10, 15))

        stats_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))

        # Configure grid for 4 equal columns
        for i in range(4):
            stats_frame.grid_columnconfigure(i, weight=1, uniform="stats")

        stat_data = [
            (str(self._stats.total), "Total Files", COLORS["text_primary"]),
            (str(self._stats.downloaded), "Downloaded", COLORS["success"]),
            (str(self._stats.pending), "Pending", COLORS["warning"]),
            (str(self._stats.videos_for_transcription), "To Transcribe", COLORS["accent"]),
        ]

        for i, (value, label, color) in enumerate(stat_data):
            self._create_stat_card(stats_frame, value, label, color, i)

        # Action buttons section
        actions_label = ctk.CTkLabel(
            scroll,
            text="Actions",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        actions_label.pack(anchor="w", pady=(10, 15))

        actions_frame = ctk.CTkFrame(
            scroll,
            fg_color=COLORS["bg_card"],
            corner_radius=15
        )
        actions_frame.pack(fill="x", pady=(0, 20))

        actions_inner = ctk.CTkFrame(actions_frame, fg_color="transparent")
        actions_inner.pack(fill="x", padx=25, pady=25)

        # Download actions row
        download_row = ctk.CTkFrame(actions_inner, fg_color="transparent")
        download_row.pack(fill="x", pady=(0, 15))

        download_label = ctk.CTkLabel(
            download_row,
            text="Download",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        download_label.pack(side="left")

        if self._is_authenticated:
            if self._is_downloading:
                # Show pause/stop buttons
                stop_btn = ctk.CTkButton(
                    download_row,
                    text="Stop",
                    command=self._on_stop_download,
                    width=80,
                    height=35,
                    fg_color=COLORS["error"],
                    hover_color="#d63d5c",
                    corner_radius=8
                )
                stop_btn.pack(side="right", padx=(10, 0))

                if self._is_paused:
                    pause_btn = ctk.CTkButton(
                        download_row,
                        text="Resume",
                        command=self._on_resume_download,
                        width=90,
                        height=35,
                        fg_color=COLORS["success"],
                        hover_color="#05c090",
                        corner_radius=8
                    )
                else:
                    pause_btn = ctk.CTkButton(
                        download_row,
                        text="Pause",
                        command=self._on_pause_download,
                        width=80,
                        height=35,
                        fg_color=COLORS["warning"],
                        hover_color="#e6bc5a",
                        corner_radius=8
                    )
                pause_btn.pack(side="right", padx=(10, 0))

                status = ctk.CTkLabel(
                    download_row,
                    text="Downloading..." if not self._is_paused else "Paused",
                    font=ctk.CTkFont(size=13),
                    text_color=COLORS["success"] if not self._is_paused else COLORS["warning"]
                )
                status.pack(side="right", padx=(0, 20))
            else:
                start_btn = ctk.CTkButton(
                    download_row,
                    text="Start Download",
                    command=self._on_start_download,
                    width=140,
                    height=35,
                    fg_color=COLORS["accent"],
                    hover_color=COLORS["accent_hover"],
                    corner_radius=8
                )
                start_btn.pack(side="right", padx=(10, 0))

                scan_btn = ctk.CTkButton(
                    download_row,
                    text="Scan Only",
                    command=self._on_scan,
                    width=100,
                    height=35,
                    fg_color="transparent",
                    border_width=1,
                    border_color=COLORS["border"],
                    hover_color=COLORS["bg_card_hover"],
                    corner_radius=8
                )
                scan_btn.pack(side="right")
        else:
            disabled_label = ctk.CTkLabel(
                download_row,
                text="Sign in to start downloading",
                font=ctk.CTkFont(size=13),
                text_color=COLORS["text_muted"]
            )
            disabled_label.pack(side="right")

        # Divider
        divider = ctk.CTkFrame(actions_inner, height=1, fg_color=COLORS["border"])
        divider.pack(fill="x", pady=15)

        # Transcription actions row
        trans_row = ctk.CTkFrame(actions_inner, fg_color="transparent")
        trans_row.pack(fill="x")

        trans_label = ctk.CTkLabel(
            trans_row,
            text="Transcription",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        trans_label.pack(side="left")

        if self._is_transcribing:
            stop_trans_btn = ctk.CTkButton(
                trans_row,
                text="Stop",
                command=self._on_stop_transcription,
                width=80,
                height=35,
                fg_color=COLORS["error"],
                hover_color="#d63d5c",
                corner_radius=8
            )
            stop_trans_btn.pack(side="right")

            trans_status = ctk.CTkLabel(
                trans_row,
                text="Transcribing...",
                font=ctk.CTkFont(size=13),
                text_color=COLORS["accent"]
            )
            trans_status.pack(side="right", padx=(0, 20))
        elif self._stats.videos_for_transcription > 0:
            trans_btn = ctk.CTkButton(
                trans_row,
                text=f"Transcribe ({self._stats.videos_for_transcription})",
                command=self._on_transcribe,
                width=140,
                height=35,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                corner_radius=8
            )
            trans_btn.pack(side="right")
        else:
            no_trans_label = ctk.CTkLabel(
                trans_row,
                text="No videos to transcribe",
                font=ctk.CTkFont(size=13),
                text_color=COLORS["text_muted"]
            )
            no_trans_label.pack(side="right")

        # Quick links
        links_label = ctk.CTkLabel(
            scroll,
            text="Quick Links",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        links_label.pack(anchor="w", pady=(10, 15))

        links_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        links_frame.pack(fill="x")

        drive_btn = ctk.CTkButton(
            links_frame,
            text="🔗  Google Drive",
            command=lambda: webbrowser.open("https://drive.google.com"),
            width=150,
            height=40,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["bg_card_hover"],
            corner_radius=10
        )
        drive_btn.pack(side="left", padx=(0, 10))

        photos_btn = ctk.CTkButton(
            links_frame,
            text="🔗  Google Photos",
            command=lambda: webbrowser.open("https://photos.google.com"),
            width=150,
            height=40,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["bg_card_hover"],
            corner_radius=10
        )
        photos_btn.pack(side="left")

    def _create_stat_card(self, parent, value: str, label: str, color: str, column: int) -> None:
        """Create a statistics card."""
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_card"],
            corner_radius=12
        )
        card.grid(row=0, column=column, padx=8, pady=5, sticky="nsew")

        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=color
        )
        value_label.pack(pady=(20, 5))

        name_label = ctk.CTkLabel(
            card,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        name_label.pack(pady=(0, 20))

    def _show_downloads_tab(self) -> None:
        """Show the downloads tab content."""
        # Header
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        header = ctk.CTkLabel(
            header_frame,
            text="Downloads",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        header.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="View and manage your downloaded files",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        )
        subtitle.pack(anchor="w", pady=(5, 0))

        # Scrollable list
        scroll_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color="transparent"
        )
        scroll_frame.pack(fill="both", expand=True)

        # Get files from config manager
        try:
            from utils.config import get_config_manager
            config_manager = get_config_manager()

            all_files = []
            for fs in config_manager.get_drive_state().values():
                all_files.append(fs)
            for fs in config_manager.get_photos_state().values():
                all_files.append(fs)

            if not all_files:
                empty_frame = ctk.CTkFrame(scroll_frame, fg_color=COLORS["bg_card"], corner_radius=15)
                empty_frame.pack(fill="x", pady=20)

                empty_label = ctk.CTkLabel(
                    empty_frame,
                    text="📭  No files found",
                    font=ctk.CTkFont(size=18),
                    text_color=COLORS["text_secondary"]
                )
                empty_label.pack(pady=40)

                hint_label = ctk.CTkLabel(
                    empty_frame,
                    text="Click 'Start Download' on the Home tab to begin",
                    font=ctk.CTkFont(size=13),
                    text_color=COLORS["text_muted"]
                )
                hint_label.pack(pady=(0, 40))
            else:
                for file_state in all_files:
                    self._create_file_row(scroll_frame, file_state)

        except Exception as e:
            logger.error(f"Error loading downloads: {e}")
            error_label = ctk.CTkLabel(
                scroll_frame,
                text=f"Error loading files: {e}",
                text_color=COLORS["error"]
            )
            error_label.pack(pady=20)

    def _create_file_row(self, parent, file_state: FileState) -> None:
        """Create a row for a file in the downloads list."""
        from utils.formatters import format_file_size

        row = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=10)
        row.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=12)

        # Status indicator
        if file_state.status == "complete":
            status_icon = "✓"
            status_color = COLORS["success"]
        elif file_state.status == "downloading":
            status_icon = "↓"
            status_color = COLORS["accent"]
        elif file_state.status == "error":
            status_icon = "✗"
            status_color = COLORS["error"]
        else:
            status_icon = "○"
            status_color = COLORS["text_muted"]

        status = ctk.CTkLabel(
            inner,
            text=status_icon,
            width=30,
            text_color=status_color,
            font=ctk.CTkFont(size=16)
        )
        status.pack(side="left")

        # File name
        name_text = file_state.name[:45] + ("..." if len(file_state.name) > 45 else "")
        name = ctk.CTkLabel(
            inner,
            text=name_text,
            anchor="w",
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=13)
        )
        name.pack(side="left", fill="x", expand=True, padx=10)

        # Source badge
        source_color = COLORS["google_blue"] if file_state.source == "drive" else COLORS["google_green"]
        source = ctk.CTkLabel(
            inner,
            text=file_state.source.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=source_color,
            width=60
        )
        source.pack(side="right", padx=10)

        # File size
        if file_state.size > 0:
            size_text = format_file_size(file_state.size)
            size = ctk.CTkLabel(
                inner,
                text=size_text,
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_secondary"],
                width=70
            )
            size.pack(side="right")

    def _show_transcriptions_tab(self) -> None:
        """Show the transcriptions tab content."""
        # Header
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        header = ctk.CTkLabel(
            header_frame,
            text="Transcriptions",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        header.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Video transcriptions using Whisper AI",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        )
        subtitle.pack(anchor="w", pady=(5, 0))

        # Status card
        status_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=15
        )
        status_card.pack(fill="x", pady=(0, 20))

        status_inner = ctk.CTkFrame(status_card, fg_color="transparent")
        status_inner.pack(fill="x", padx=25, pady=20)

        pending_count = self._stats.videos_for_transcription

        if self._is_transcribing:
            status_text = "Transcription in progress..."
            status_color = COLORS["accent"]
        elif pending_count > 0:
            status_text = f"{pending_count} video(s) ready for transcription"
            status_color = COLORS["warning"]
        else:
            status_text = "No videos pending transcription"
            status_color = COLORS["text_muted"]

        status_label = ctk.CTkLabel(
            status_inner,
            text=status_text,
            font=ctk.CTkFont(size=15),
            text_color=status_color
        )
        status_label.pack(side="left")

        # Action button
        if self._is_transcribing:
            stop_btn = ctk.CTkButton(
                status_inner,
                text="Stop Transcription",
                command=self._on_stop_transcription,
                width=150,
                height=35,
                fg_color=COLORS["error"],
                hover_color="#d63d5c",
                corner_radius=8
            )
            stop_btn.pack(side="right")
        elif pending_count > 0:
            start_btn = ctk.CTkButton(
                status_inner,
                text="Start Transcription",
                command=self._on_transcribe,
                width=150,
                height=35,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                corner_radius=8
            )
            start_btn.pack(side="right")

        # Transcription list
        list_label = ctk.CTkLabel(
            self.content_frame,
            text="Transcription History",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        list_label.pack(anchor="w", pady=(10, 10))

        scroll_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color="transparent"
        )
        scroll_frame.pack(fill="both", expand=True)

        try:
            from utils.config import get_config_manager
            config_manager = get_config_manager()
            transcription_state = config_manager.get_transcription_state()

            if not transcription_state:
                empty_frame = ctk.CTkFrame(scroll_frame, fg_color=COLORS["bg_card"], corner_radius=15)
                empty_frame.pack(fill="x", pady=10)

                empty_label = ctk.CTkLabel(
                    empty_frame,
                    text="📝  No transcriptions yet",
                    font=ctk.CTkFont(size=16),
                    text_color=COLORS["text_secondary"]
                )
                empty_label.pack(pady=30)
            else:
                for video_path, state in transcription_state.items():
                    self._create_transcription_row(scroll_frame, video_path, state)

        except Exception as e:
            logger.error(f"Error loading transcriptions: {e}")

    def _create_transcription_row(self, parent, video_path: str, state) -> None:
        """Create a row for a transcription."""
        row = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=10)
        row.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=12)

        # Status
        if state.status == "complete":
            status_icon = "✓"
            status_color = COLORS["success"]
        elif state.status == "transcribing":
            status_icon = "⟳"
            status_color = COLORS["accent"]
        elif state.status == "error":
            status_icon = "✗"
            status_color = COLORS["error"]
        else:
            status_icon = "○"
            status_color = COLORS["text_muted"]

        status = ctk.CTkLabel(
            inner,
            text=status_icon,
            width=30,
            text_color=status_color,
            font=ctk.CTkFont(size=16)
        )
        status.pack(side="left")

        # File name
        name = Path(video_path).name
        name_text = name[:50] + ("..." if len(name) > 50 else "")
        name_label = ctk.CTkLabel(
            inner,
            text=name_text,
            anchor="w",
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=13)
        )
        name_label.pack(side="left", fill="x", expand=True, padx=10)

        # Status text
        status_text_label = ctk.CTkLabel(
            inner,
            text=state.status.capitalize(),
            font=ctk.CTkFont(size=11),
            text_color=status_color
        )
        status_text_label.pack(side="right")

    def _refresh_ui(self) -> None:
        """Refresh the current tab."""
        self._switch_tab(self._current_tab)

    def _create_tk_window(self) -> None:
        """Create window using standard Tkinter (fallback)."""
        self.window = tk.Tk()
        self.window.title("Google Media Backup")
        self.window.geometry("800x600")

        label = ttk.Label(
            self.window,
            text="CustomTkinter not available.\nInstall with: pip install customtkinter"
        )
        label.pack(pady=50)


# Singleton instance
_main_window: Optional[MainWindow] = None


def get_main_window() -> MainWindow:
    """Get the global MainWindow instance."""
    global _main_window
    if _main_window is None:
        _main_window = MainWindow()
    return _main_window
