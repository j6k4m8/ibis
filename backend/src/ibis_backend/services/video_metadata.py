"""Video metadata helpers."""

from __future__ import annotations

import json
from typing import Optional
from urllib import parse, request


def is_youtube_url(url: str) -> bool:
    """Return True if the URL is a YouTube link."""

    lowered = url.lower()
    return "youtube.com" in lowered or "youtu.be" in lowered


def fetch_youtube_title(url: str, timeout_seconds: float = 2.0) -> Optional[str]:
    """Fetch the YouTube title via oEmbed.

    Args:
        url: YouTube video URL.
        timeout_seconds: Request timeout.

    Returns:
        Optional[str]: Title if resolved.
    """

    if not is_youtube_url(url):
        return None

    query = parse.urlencode({"url": url, "format": "json"})
    oembed_url = f"https://www.youtube.com/oembed?{query}"
    try:
        with request.urlopen(oembed_url, timeout=timeout_seconds) as response:
            payload = response.read().decode("utf-8")
    except Exception:
        return None

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    title = data.get("title")
    if not isinstance(title, str):
        return None
    return title.strip() or None
