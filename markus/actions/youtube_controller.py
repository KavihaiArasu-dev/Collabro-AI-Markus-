"""
Markus AI — YouTube Controller (inspired by Jarvis youtube_video.py)

Search for and play YouTube videos directly from voice commands.
Uses URL construction and pywhatkit/webbrowser for playback.

Features:
- Search YouTube videos
- Play first result (or specific video)
- Play music by song name
- Return video title, URL, duration
"""

from __future__ import annotations

import logging
import urllib.parse
import webbrowser
from typing import Optional

logger = logging.getLogger(__name__)

# ── Try to import youtube search library ──
_HAS_YTSEARCH = False
try:
    from youtubesearchpython import VideosSearch  # type: ignore
    _HAS_YTSEARCH = True
except ImportError:
    logger.info("youtube-search-python not installed. YouTube search will use URL fallback.")

# ── Try pywhatkit for direct playback ──
_HAS_PYWHATKIT = False
try:
    import pywhatkit  # type: ignore
    _HAS_PYWHATKIT = True
except ImportError:
    pass


class YouTubeController:
    """YouTube search and playback controller."""

    def search(self, query: str, max_results: int = 5) -> dict:
        """
        Search YouTube for videos.

        Returns:
            dict with results list (title, url, duration, channel, views) and summary
        """
        if not _HAS_YTSEARCH:
            return self._url_fallback_search(query)

        try:
            search = VideosSearch(query, limit=max_results)
            raw_results = search.result().get("result", [])

            results = []
            for r in raw_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "duration": r.get("duration", ""),
                    "channel": r.get("channel", {}).get("name", ""),
                    "views": r.get("viewCount", {}).get("short", ""),
                    "thumbnail": r.get("thumbnails", [{}])[0].get("url", "") if r.get("thumbnails") else "",
                })

            summary_lines = [f"YouTube results for '{query}':\n"]
            for i, r in enumerate(results, 1):
                summary_lines.append(f"{i}. **{r['title']}**")
                if r["channel"]:
                    summary_lines.append(f"   Channel: {r['channel']} | Duration: {r['duration']} | Views: {r['views']}")
                summary_lines.append(f"   🔗 {r['url']}")
                summary_lines.append("")

            logger.info(f"YouTube search for '{query}' returned {len(results)} results")
            return {
                "results": results,
                "summary": "\n".join(summary_lines),
                "query": query,
            }

        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return self._url_fallback_search(query)

    def play(self, query: str) -> str:
        """
        Search and play the first YouTube result.

        Tries multiple methods:
        1. youtubesearchpython → get URL → open in browser
        2. pywhatkit.playonyt()
        3. Direct YouTube search URL
        """
        # Method 1: Search and open first result
        if _HAS_YTSEARCH:
            try:
                search = VideosSearch(query, limit=1)
                raw_results = search.result().get("result", [])
                if raw_results:
                    video = raw_results[0]
                    url = video.get("link", "")
                    title = video.get("title", query)
                    if url:
                        webbrowser.open(url)
                        logger.info(f"Playing YouTube video: {title}")
                        return f"Now playing: {title}\n🔗 {url}"
            except Exception as e:
                logger.warning(f"YouTube search-and-play failed: {e}")

        # Method 2: pywhatkit
        if _HAS_PYWHATKIT:
            try:
                pywhatkit.playonyt(query)
                return f"Playing '{query}' on YouTube"
            except Exception as e:
                logger.warning(f"pywhatkit playback failed: {e}")

        # Method 3: Direct YouTube search URL
        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(search_url)
        return f"Searching YouTube for '{query}' in browser"

    def play_music(self, song_name: str) -> str:
        """
        Play a song on YouTube.

        Appends "official audio" to the search for better music results.
        """
        query = f"{song_name} official audio"
        return self.play(query)

    def _url_fallback_search(self, query: str) -> dict:
        """Fallback: open YouTube search in browser."""
        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(search_url)
        return {
            "results": [],
            "summary": f"Opened YouTube search for '{query}' in browser",
            "query": query,
            "opened_in_browser": True,
        }


# Singleton
youtube_controller = YouTubeController()
