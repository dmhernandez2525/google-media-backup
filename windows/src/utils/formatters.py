"""
Formatting utilities for Google Media Backup.
Provides human-readable formats for file sizes and dates.
"""

from datetime import datetime
from typing import Optional


def format_file_size(size_bytes: int) -> str:
    """
    Format a file size in bytes to a human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string like "1.2 MB"
    """
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def format_relative_date(date_string: Optional[str]) -> str:
    """
    Format an ISO date string to a relative time string.

    Args:
        date_string: ISO format date string

    Returns:
        Formatted string like "2 hours ago"
    """
    if not date_string:
        return ""

    try:
        from dateutil.parser import parse
        date = parse(date_string)

        # Remove timezone info for comparison if present
        if date.tzinfo is not None:
            date = date.replace(tzinfo=None)

        now = datetime.now()
        diff = now - date

        seconds = diff.total_seconds()

        if seconds < 0:
            return "just now"
        elif seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        else:
            return date.strftime("%b %d, %Y")

    except Exception:
        return ""
