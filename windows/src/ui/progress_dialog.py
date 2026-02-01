"""
Progress dialog for long-running operations.
"""

from typing import Optional

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk
    CTK_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger()


class ProgressDialog:
    """Simple progress dialog for operations."""

    def __init__(self, parent=None, title: str = "Please wait..."):
        self.parent = parent
        self.title = title
        self.window: Optional[ctk.CTkToplevel] = None
        self._message_label = None
        self._progress_bar = None

    def show(self, message: str = "Processing...") -> None:
        """Show the progress dialog."""
        if self.window is not None:
            return

        if CTK_AVAILABLE:
            self._create_ctk_window(message)
        else:
            self._create_tk_window(message)

    def _create_ctk_window(self, message: str) -> None:
        """Create window using CustomTkinter."""
        if self.parent:
            self.window = ctk.CTkToplevel(self.parent)
        else:
            self.window = ctk.CTkToplevel()

        self.window.title(self.title)
        self.window.geometry("350x120")
        self.window.resizable(False, False)

        # Center on screen
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 350) // 2
        y = (self.window.winfo_screenheight() - 120) // 2
        self.window.geometry(f"350x120+{x}+{y}")

        # Keep on top
        self.window.attributes("-topmost", True)

        # Disable close button
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)

        # Main frame
        frame = ctk.CTkFrame(self.window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Message
        self._message_label = ctk.CTkLabel(
            frame,
            text=message,
            font=ctk.CTkFont(size=13)
        )
        self._message_label.pack(pady=(10, 15))

        # Progress bar
        self._progress_bar = ctk.CTkProgressBar(frame, mode="indeterminate")
        self._progress_bar.pack(fill="x", padx=20)
        self._progress_bar.start()

    def _create_tk_window(self, message: str) -> None:
        """Create window using standard Tkinter (fallback)."""
        if self.parent:
            self.window = tk.Toplevel(self.parent)
        else:
            self.window = tk.Tk()

        self.window.title(self.title)
        self.window.geometry("350x120")
        self.window.resizable(False, False)

        # Center
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 350) // 2
        y = (self.window.winfo_screenheight() - 120) // 2
        self.window.geometry(f"350x120+{x}+{y}")

        self.window.attributes("-topmost", True)

        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill="both", expand=True)

        self._message_label = ttk.Label(frame, text=message)
        self._message_label.pack(pady=(10, 15))

        self._progress_bar = ttk.Progressbar(frame, mode="indeterminate")
        self._progress_bar.pack(fill="x", padx=20)
        self._progress_bar.start()

    def update_message(self, message: str) -> None:
        """Update the progress message."""
        if self._message_label and self.window:
            if CTK_AVAILABLE:
                self.window.after(0, lambda: self._message_label.configure(text=message))
            else:
                self.window.after(0, lambda: self._message_label.config(text=message))

    def close(self) -> None:
        """Close the progress dialog."""
        if self._progress_bar:
            try:
                self._progress_bar.stop()
            except Exception:
                pass

        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None


def show_progress(parent=None, title: str = "Please wait...", message: str = "Processing...") -> ProgressDialog:
    """Show a progress dialog and return the instance."""
    dialog = ProgressDialog(parent, title)
    dialog.show(message)
    return dialog
