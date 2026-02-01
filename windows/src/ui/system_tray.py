"""
System tray icon and menu for Google Media Backup.
Provides quick access to app functions from the Windows system tray.
"""

import os
import threading
from pathlib import Path
from typing import Optional, Callable

from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item, Menu

from utils.logger import get_logger

logger = get_logger()


class SystemTray:
    """System tray icon and menu manager."""

    def __init__(self):
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

        # State
        self._is_authenticated = False
        self._is_downloading = False
        self._is_transcribing = False
        self._pending_transcriptions = 0

        # Callbacks
        self._on_sign_in: Optional[Callable[[], None]] = None
        self._on_sign_out: Optional[Callable[[], None]] = None
        self._on_start_download: Optional[Callable[[], None]] = None
        self._on_stop_download: Optional[Callable[[], None]] = None
        self._on_transcribe: Optional[Callable[[], None]] = None
        self._on_stop_transcription: Optional[Callable[[], None]] = None
        self._on_open_folder: Optional[Callable[[], None]] = None
        self._on_show_panel: Optional[Callable[[], None]] = None
        self._on_preferences: Optional[Callable[[], None]] = None
        self._on_quit: Optional[Callable[[], None]] = None

    def set_callbacks(
        self,
        on_sign_in: Optional[Callable[[], None]] = None,
        on_sign_out: Optional[Callable[[], None]] = None,
        on_start_download: Optional[Callable[[], None]] = None,
        on_stop_download: Optional[Callable[[], None]] = None,
        on_transcribe: Optional[Callable[[], None]] = None,
        on_stop_transcription: Optional[Callable[[], None]] = None,
        on_open_folder: Optional[Callable[[], None]] = None,
        on_show_panel: Optional[Callable[[], None]] = None,
        on_preferences: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None
    ) -> None:
        """Set callback functions for menu actions."""
        self._on_sign_in = on_sign_in
        self._on_sign_out = on_sign_out
        self._on_start_download = on_start_download
        self._on_stop_download = on_stop_download
        self._on_transcribe = on_transcribe
        self._on_stop_transcription = on_stop_transcription
        self._on_open_folder = on_open_folder
        self._on_show_panel = on_show_panel
        self._on_preferences = on_preferences
        self._on_quit = on_quit

    def update_state(
        self,
        is_authenticated: Optional[bool] = None,
        is_downloading: Optional[bool] = None,
        is_transcribing: Optional[bool] = None,
        pending_transcriptions: Optional[int] = None
    ) -> None:
        """Update the tray state and refresh the menu."""
        if is_authenticated is not None:
            self._is_authenticated = is_authenticated
        if is_downloading is not None:
            self._is_downloading = is_downloading
        if is_transcribing is not None:
            self._is_transcribing = is_transcribing
        if pending_transcriptions is not None:
            self._pending_transcriptions = pending_transcriptions

        # Update icon and menu
        self._update_icon()
        self._update_menu()

    def _create_icon_image(self, syncing: bool = False) -> Image.Image:
        """Create the tray icon image."""
        # Try to load from resources first
        script_dir = Path(__file__).parent.parent.parent
        if syncing:
            icon_path = script_dir / "resources" / "icon_syncing.ico"
        else:
            icon_path = script_dir / "resources" / "icon.ico"

        if icon_path.exists():
            try:
                return Image.open(icon_path)
            except Exception:
                pass

        # Create a simple icon programmatically
        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Draw a cloud shape (simplified)
        if syncing:
            color = (66, 133, 244, 255)  # Google blue
        else:
            color = (128, 128, 128, 255)  # Gray

        # Cloud body
        draw.ellipse([10, 25, 35, 50], fill=color)
        draw.ellipse([25, 20, 55, 50], fill=color)
        draw.ellipse([40, 25, 60, 50], fill=color)
        draw.rectangle([15, 35, 55, 50], fill=color)

        # Add arrow if syncing
        if syncing:
            arrow_color = (255, 255, 255, 255)
            draw.polygon([(32, 55), (25, 48), (39, 48)], fill=arrow_color)
            draw.rectangle([29, 42, 35, 50], fill=arrow_color)

        return image

    def _update_icon(self) -> None:
        """Update the tray icon based on current state."""
        if self._icon is None:
            return

        syncing = self._is_downloading or self._is_transcribing
        new_icon = self._create_icon_image(syncing)

        try:
            self._icon.icon = new_icon
        except Exception as e:
            logger.warning(f"Failed to update icon: {e}")

        # Update tooltip
        if self._is_downloading:
            tooltip = "Google Media Backup - Downloading..."
        elif self._is_transcribing:
            tooltip = "Google Media Backup - Transcribing..."
        elif self._is_authenticated:
            tooltip = "Google Media Backup - Ready"
        else:
            tooltip = "Google Media Backup - Not signed in"

        try:
            self._icon.title = tooltip
        except Exception:
            pass

    def _update_menu(self) -> None:
        """Update the menu based on current state."""
        if self._icon is None:
            return

        self._icon.menu = self._create_menu()

    def _create_menu(self) -> Menu:
        """Create the context menu."""
        items = []

        # Auth items
        if self._is_authenticated:
            items.append(Item("Signed in", None, enabled=False))
            items.append(Item("Sign Out", self._handle_sign_out))
        else:
            items.append(Item("Sign In", self._handle_sign_in))

        items.append(Menu.SEPARATOR)

        # Download items
        if self._is_authenticated:
            if self._is_downloading:
                items.append(Item("Downloading...", None, enabled=False))
                items.append(Item("Stop Download", self._handle_stop_download))
            else:
                items.append(Item("Start Download", self._handle_start_download))

            # Transcription
            if self._is_transcribing:
                items.append(Item("Transcribing...", None, enabled=False))
                items.append(Item("Stop Transcription", self._handle_stop_transcription))
            else:
                transcribe_label = "Transcribe Videos"
                if self._pending_transcriptions > 0:
                    transcribe_label = f"Transcribe Videos ({self._pending_transcriptions})"

                items.append(Item(
                    transcribe_label,
                    self._handle_transcribe,
                    enabled=self._pending_transcriptions > 0
                ))

        items.append(Menu.SEPARATOR)

        # Utility items
        items.append(Item("Open Downloads Folder", self._handle_open_folder))
        items.append(Item("Show Panel", self._handle_show_panel, default=True))
        items.append(Item("Preferences", self._handle_preferences))

        items.append(Menu.SEPARATOR)

        items.append(Item("Quit", self._handle_quit))

        return Menu(*items)

    def _handle_sign_in(self, icon, item) -> None:
        if self._on_sign_in:
            self._on_sign_in()

    def _handle_sign_out(self, icon, item) -> None:
        if self._on_sign_out:
            self._on_sign_out()

    def _handle_start_download(self, icon, item) -> None:
        if self._on_start_download:
            self._on_start_download()

    def _handle_stop_download(self, icon, item) -> None:
        if self._on_stop_download:
            self._on_stop_download()

    def _handle_transcribe(self, icon, item) -> None:
        if self._on_transcribe:
            self._on_transcribe()

    def _handle_stop_transcription(self, icon, item) -> None:
        if self._on_stop_transcription:
            self._on_stop_transcription()

    def _handle_open_folder(self, icon, item) -> None:
        if self._on_open_folder:
            self._on_open_folder()

    def _handle_show_panel(self, icon, item) -> None:
        if self._on_show_panel:
            self._on_show_panel()

    def _handle_preferences(self, icon, item) -> None:
        if self._on_preferences:
            self._on_preferences()

    def _handle_quit(self, icon, item) -> None:
        if self._on_quit:
            self._on_quit()
        self.stop()

    def start(self) -> None:
        """Start the system tray icon in a background thread."""
        if self._icon is not None:
            return

        icon_image = self._create_icon_image(syncing=False)

        self._icon = pystray.Icon(
            "google-media-backup",
            icon_image,
            "Google Media Backup",
            menu=self._create_menu()
        )

        # Run in background thread
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

        logger.info("System tray started")

    def stop(self) -> None:
        """Stop the system tray icon."""
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

        logger.info("System tray stopped")


# Singleton instance
_system_tray: Optional[SystemTray] = None


def get_system_tray() -> SystemTray:
    """Get the global SystemTray instance."""
    global _system_tray
    if _system_tray is None:
        _system_tray = SystemTray()
    return _system_tray
