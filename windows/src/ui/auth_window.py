"""
Authentication window for Google sign-in flow.
Provides UI feedback during the OAuth process.
"""

import threading
from typing import Optional, Callable

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk
    CTK_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger()


class AuthWindow:
    """Window shown during authentication process."""

    def __init__(self, parent=None):
        self.parent = parent
        self.window: Optional[ctk.CTkToplevel] = None
        self._on_complete: Optional[Callable[[bool, str], None]] = None

    def show(self, on_complete: Optional[Callable[[bool, str], None]] = None) -> None:
        """
        Show the authentication window and start OAuth flow.

        Args:
            on_complete: Callback when auth completes (success: bool, message: str)
        """
        self._on_complete = on_complete

        if CTK_AVAILABLE:
            self._create_ctk_window()
        else:
            self._create_tk_window()

    def _create_ctk_window(self) -> None:
        """Create window using CustomTkinter."""
        if self.parent:
            self.window = ctk.CTkToplevel(self.parent)
        else:
            self.window = ctk.CTkToplevel()

        self.window.title("Sign in to Google")
        self.window.geometry("400x200")
        self.window.resizable(False, False)

        # Center on screen
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 400) // 2
        y = (self.window.winfo_screenheight() - 200) // 2
        self.window.geometry(f"400x200+{x}+{y}")

        # Keep on top
        self.window.attributes("-topmost", True)

        # Main frame
        frame = ctk.CTkFrame(self.window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title = ctk.CTkLabel(
            frame,
            text="Signing in to Google...",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=(10, 5))

        # Status message
        self.status_label = ctk.CTkLabel(
            frame,
            text="A browser window will open for authentication.\nPlease complete the sign-in process.",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=10)

        # Progress bar
        self.progress = ctk.CTkProgressBar(frame, mode="indeterminate")
        self.progress.pack(pady=10, fill="x", padx=20)
        self.progress.start()

        # Cancel button
        self.cancel_btn = ctk.CTkButton(
            frame,
            text="Cancel",
            command=self._on_cancel,
            width=100
        )
        self.cancel_btn.pack(pady=10)

        # Start auth in background thread
        self._start_auth()

    def _create_tk_window(self) -> None:
        """Create window using standard Tkinter (fallback)."""
        if self.parent:
            self.window = tk.Toplevel(self.parent)
        else:
            self.window = tk.Tk()

        self.window.title("Sign in to Google")
        self.window.geometry("400x200")
        self.window.resizable(False, False)

        # Center on screen
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 400) // 2
        y = (self.window.winfo_screenheight() - 200) // 2
        self.window.geometry(f"400x200+{x}+{y}")

        # Keep on top
        self.window.attributes("-topmost", True)

        # Main frame
        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill="both", expand=True)

        # Title
        title = ttk.Label(
            frame,
            text="Signing in to Google...",
            font=("Segoe UI", 14, "bold")
        )
        title.pack(pady=(10, 5))

        # Status message
        self.status_label = ttk.Label(
            frame,
            text="A browser window will open for authentication.\nPlease complete the sign-in process."
        )
        self.status_label.pack(pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(pady=10, fill="x", padx=20)
        self.progress.start()

        # Cancel button
        self.cancel_btn = ttk.Button(
            frame,
            text="Cancel",
            command=self._on_cancel
        )
        self.cancel_btn.pack(pady=10)

        # Start auth in background thread
        self._start_auth()

    def _start_auth(self) -> None:
        """Start the authentication process in a background thread."""
        def auth_thread():
            from core.google_auth import get_auth_manager

            auth_manager = get_auth_manager()

            def on_auth_complete(success: bool, message: str):
                # Schedule UI update on main thread
                if self.window:
                    self.window.after(0, lambda: self._auth_complete(success, message))

            success = auth_manager.sign_in(callback=on_auth_complete)

            if not success and self.window:
                self.window.after(0, lambda: self._auth_complete(False, "Authentication failed"))

        thread = threading.Thread(target=auth_thread, daemon=True)
        thread.start()

    def _auth_complete(self, success: bool, message: str) -> None:
        """Handle authentication completion."""
        if self.progress:
            self.progress.stop()

        if success:
            if self.status_label:
                if CTK_AVAILABLE:
                    self.status_label.configure(text="Successfully signed in!")
                else:
                    self.status_label.config(text="Successfully signed in!")

            # Close window after short delay
            if self.window:
                self.window.after(1500, self._close)
        else:
            if self.status_label:
                if CTK_AVAILABLE:
                    self.status_label.configure(text=f"Sign-in failed:\n{message}")
                else:
                    self.status_label.config(text=f"Sign-in failed:\n{message}")

            if self.cancel_btn:
                if CTK_AVAILABLE:
                    self.cancel_btn.configure(text="Close")
                else:
                    self.cancel_btn.config(text="Close")

        if self._on_complete:
            self._on_complete(success, message)

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self._close()
        if self._on_complete:
            self._on_complete(False, "Cancelled by user")

    def _close(self) -> None:
        """Close the window."""
        if self.window:
            self.window.destroy()
            self.window = None


def show_auth_dialog(parent=None, on_complete: Optional[Callable[[bool, str], None]] = None) -> AuthWindow:
    """
    Show the authentication dialog.

    Args:
        parent: Parent window
        on_complete: Callback when auth completes

    Returns:
        AuthWindow instance
    """
    window = AuthWindow(parent)
    window.show(on_complete)
    return window
