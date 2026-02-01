"""
Google OAuth 2.0 authentication manager.
Handles OAuth flow, token storage, and refresh for Google Drive and Photos APIs.
"""

import os
import json
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Callable

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from utils.paths import Paths
from utils.logger import get_logger

logger = get_logger()


# OAuth scopes for Google Drive and Photos
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly"
]


class GoogleAuthManager:
    """Manages Google OAuth 2.0 authentication."""

    def __init__(self):
        self._credentials: Optional[Credentials] = None
        self._on_auth_change: Optional[Callable[[bool], None]] = None

    @property
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated with valid credentials."""
        if self._credentials is None:
            self._credentials = self._load_credentials()

        if self._credentials is None:
            return False

        # Check if credentials are valid and not expired
        if self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                self._save_credentials()
                return True
            except Exception as e:
                logger.warning(f"Failed to refresh credentials: {e}")
                return False

        return self._credentials.valid

    @property
    def credentials(self) -> Optional[Credentials]:
        """Get the current credentials, refreshing if needed."""
        if not self.is_authenticated:
            return None
        return self._credentials

    def set_auth_change_callback(self, callback: Callable[[bool], None]) -> None:
        """Set callback for auth state changes."""
        self._on_auth_change = callback

    def show_setup_instructions(self) -> None:
        """Show a dialog with instructions for setting up Google credentials."""
        try:
            from tkinter import messagebox
            config_dir = Paths.get_config_dir()

            message = (
                "To use Google Media Backup, you need to set up Google OAuth credentials:\n\n"
                "1. Go to: https://console.cloud.google.com/\n"
                "2. Create a new project (or select existing)\n"
                "3. Go to 'APIs & Services' > 'Enable APIs'\n"
                "4. Enable 'Google Drive API' and 'Photos Library API'\n"
                "5. Go to 'APIs & Services' > 'Credentials'\n"
                "6. Create OAuth 2.0 credentials (Desktop application)\n"
                "7. Download the JSON file\n"
                f"8. Save it as:\n   {config_dir}\\credentials.json\n\n"
                "Would you like to open the Google Cloud Console now?"
            )

            result = messagebox.askyesno("Google Credentials Required", message)
            if result:
                webbrowser.open("https://console.cloud.google.com/apis/credentials")

        except Exception as e:
            logger.warning(f"Could not show setup dialog: {e}")

    def sign_in(self, callback: Optional[Callable[[bool, str], None]] = None) -> bool:
        """
        Start the OAuth sign-in flow.

        Args:
            callback: Optional callback(success: bool, message: str)

        Returns:
            True if sign-in was successful
        """
        credentials_file = Paths.get_credentials_file()

        if not credentials_file.exists():
            msg = f"Credentials file not found: {credentials_file}"
            logger.error(msg)
            # Show setup instructions
            self.show_setup_instructions()
            if callback:
                callback(False, "Credentials not configured. Please follow the setup instructions.")
            return False

        try:
            # Create OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_file),
                scopes=SCOPES
            )

            # Run local server for OAuth callback
            logger.info("Starting OAuth flow...")
            self._credentials = flow.run_local_server(
                port=8080,
                prompt="consent",
                success_message="Authentication successful! You can close this window.",
                open_browser=True
            )

            # Save credentials
            self._save_credentials()

            logger.info("Successfully authenticated with Google")
            if self._on_auth_change:
                self._on_auth_change(True)
            if callback:
                callback(True, "Successfully signed in")

            return True

        except Exception as e:
            msg = f"OAuth sign-in failed: {e}"
            logger.error(msg)
            if callback:
                callback(False, msg)
            return False

    def sign_out(self) -> None:
        """Sign out and clear stored credentials."""
        self._credentials = None

        # Delete token file
        token_file = Paths.get_token_file()
        if token_file.exists():
            try:
                token_file.unlink()
                logger.info("Signed out and removed token file")
            except Exception as e:
                logger.warning(f"Failed to delete token file: {e}")

        if self._on_auth_change:
            self._on_auth_change(False)

    def refresh_token(self) -> bool:
        """Manually refresh the access token."""
        if self._credentials is None:
            return False

        if not self._credentials.refresh_token:
            logger.warning("No refresh token available")
            return False

        try:
            self._credentials.refresh(Request())
            self._save_credentials()
            logger.info("Token refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            return False

    def get_access_token(self) -> Optional[str]:
        """Get the current access token, refreshing if needed."""
        if not self.is_authenticated:
            return None

        # Refresh if expiring soon (within 60 seconds)
        if self._credentials.expired or self._is_expiring_soon():
            if not self.refresh_token():
                return None

        return self._credentials.token

    def _is_expiring_soon(self, buffer_seconds: int = 60) -> bool:
        """Check if token is expiring within the buffer period."""
        if not self._credentials or not self._credentials.expiry:
            return True

        expiry_time = self._credentials.expiry
        # Handle timezone-naive datetime
        if expiry_time.tzinfo is None:
            buffer_time = datetime.utcnow() + timedelta(seconds=buffer_seconds)
        else:
            from datetime import timezone
            buffer_time = datetime.now(timezone.utc) + timedelta(seconds=buffer_seconds)

        return expiry_time <= buffer_time

    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from the token file."""
        token_file = Paths.get_token_file()

        if not token_file.exists():
            logger.debug("No token file found")
            return None

        try:
            with open(token_file, "r", encoding="utf-8") as f:
                token_data = json.load(f)

            credentials = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes", SCOPES)
            )

            # Set expiry if available
            if "expiry" in token_data:
                from dateutil.parser import parse
                credentials._expiry = parse(token_data["expiry"]).replace(tzinfo=None)

            logger.debug("Loaded credentials from token file")
            return credentials

        except Exception as e:
            logger.warning(f"Failed to load credentials: {e}")
            return None

    def _save_credentials(self) -> None:
        """Save credentials to the token file."""
        if self._credentials is None:
            return

        token_file = Paths.get_token_file()

        try:
            token_data = {
                "token": self._credentials.token,
                "refresh_token": self._credentials.refresh_token,
                "token_uri": self._credentials.token_uri,
                "client_id": self._credentials.client_id,
                "client_secret": self._credentials.client_secret,
                "scopes": self._credentials.scopes or SCOPES
            }

            if self._credentials.expiry:
                token_data["expiry"] = self._credentials.expiry.isoformat()

            with open(token_file, "w", encoding="utf-8") as f:
                json.dump(token_data, f, indent=2)

            logger.debug("Saved credentials to token file")

        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")


# Singleton instance
_auth_manager: Optional[GoogleAuthManager] = None


def get_auth_manager() -> GoogleAuthManager:
    """Get the global GoogleAuthManager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = GoogleAuthManager()
    return _auth_manager
