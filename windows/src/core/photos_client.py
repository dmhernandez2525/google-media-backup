"""
Google Photos API client for listing and downloading videos.
Uses the Photos Library API to access media items.
"""

import requests
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .google_auth import get_auth_manager
from utils.logger import get_logger
from utils.config import FileState

logger = get_logger()


# Video media types in Google Photos
VIDEO_MEDIA_TYPE = "VIDEO"


class PhotosClient:
    """Client for interacting with Google Photos Library API."""

    def __init__(self):
        self._service = None
        self._should_stop = False

    def _get_service(self):
        """Get or create the Photos API service."""
        if self._service is not None:
            return self._service

        auth_manager = get_auth_manager()
        credentials = auth_manager.credentials

        if credentials is None:
            raise RuntimeError("Not authenticated with Google")

        # Build the Photos Library API service
        self._service = build(
            "photoslibrary",
            "v1",
            credentials=credentials,
            static_discovery=False
        )
        return self._service

    def invalidate_service(self) -> None:
        """Invalidate the cached service (call after re-auth)."""
        self._service = None

    def list_all_videos(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[FileState]:
        """
        List all videos from Google Photos.

        Args:
            progress_callback: Optional callback(current_count, total_estimated)

        Returns:
            List of FileState objects for each video
        """
        service = self._get_service()
        videos: List[FileState] = []

        page_token = None
        page_count = 0

        try:
            while True:
                # Build request body with video filter
                request_body = {
                    "pageSize": 100,
                    "filters": {
                        "mediaTypeFilter": {
                            "mediaTypes": [VIDEO_MEDIA_TYPE]
                        }
                    }
                }

                if page_token:
                    request_body["pageToken"] = page_token

                # Search for videos
                results = service.mediaItems().search(body=request_body).execute()

                items = results.get("mediaItems", [])
                page_count += 1

                for item in items:
                    # Extract video metadata
                    metadata = item.get("mediaMetadata", {})
                    video_meta = metadata.get("video", {})

                    file_state = FileState(
                        id=item["id"],
                        name=item.get("filename", f"video_{item['id'][:8]}"),
                        source="photos",
                        mime_type=item.get("mimeType", "video/mp4"),
                        size=0,  # Photos API doesn't provide file size
                        status="pending"
                    )
                    videos.append(file_state)

                if progress_callback:
                    progress_callback(len(videos), len(videos))

                logger.debug(f"Listed {len(items)} videos from page {page_count}")

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            logger.info(f"Found {len(videos)} videos in Google Photos")
            return videos

        except HttpError as e:
            logger.error(f"Error listing Photos videos: {e}")
            raise

    def download_video(
        self,
        media_item_id: str,
        destination: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Download a video from Google Photos.

        Args:
            media_item_id: The Photos media item ID
            destination: Local path to save the file
            progress_callback: Optional callback(bytes_downloaded, total_bytes)

        Returns:
            True if download was successful
        """
        service = self._get_service()
        auth_manager = get_auth_manager()

        try:
            # Get the media item to get the base URL
            item = service.mediaItems().get(mediaItemId=media_item_id).execute()

            base_url = item.get("baseUrl")
            if not base_url:
                logger.error(f"No base URL for media item {media_item_id}")
                return False

            # For videos, append =dv to get the downloadable video
            download_url = f"{base_url}=dv"

            # Get access token for the request
            access_token = auth_manager.get_access_token()
            if not access_token:
                logger.error("No access token available")
                return False

            headers = {
                "Authorization": f"Bearer {access_token}"
            }

            # Ensure parent directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Download the video with streaming
            response = requests.get(download_url, headers=headers, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            progress_callback(progress, 100)

            # Validate file was downloaded properly (not empty)
            if destination.exists() and destination.stat().st_size == 0:
                logger.warning(f"Downloaded video is empty, removing: {destination}")
                destination.unlink()
                return False

            logger.debug(f"Downloaded video to {destination}")
            return True

        except HttpError as e:
            logger.error(f"Error downloading video {media_item_id}: {e}")
            # Clean up partial file
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            return False
        except requests.RequestException as e:
            logger.error(f"HTTP error downloading video: {e}")
            # Clean up partial file
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading video: {e}")
            # Clean up partial file
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            return False

    def get_media_item(self, media_item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific media item.

        Args:
            media_item_id: The Photos media item ID

        Returns:
            Media item dict or None if not found
        """
        service = self._get_service()

        try:
            return service.mediaItems().get(mediaItemId=media_item_id).execute()
        except HttpError as e:
            logger.error(f"Error getting media item info: {e}")
            return None

    def stop(self) -> None:
        """Signal to stop ongoing operations."""
        self._should_stop = True

    def reset(self) -> None:
        """Reset state for new operations."""
        self._should_stop = False


# Singleton instance
_photos_client: Optional[PhotosClient] = None


def get_photos_client() -> PhotosClient:
    """Get the global PhotosClient instance."""
    global _photos_client
    if _photos_client is None:
        _photos_client = PhotosClient()
    return _photos_client
