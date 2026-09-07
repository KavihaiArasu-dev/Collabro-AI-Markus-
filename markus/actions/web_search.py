"""
Markus AI — Web Search Engine (inspired by Jarvis web_search.py)

Provides web search capabilities using DuckDuckGo (no API key required).
Falls back gracefully if the search library isn't installed.

Features:
- Text search with result summaries
- News search
- Open results in browser
- Structured result output (title, snippet, URL)
"""

from __future__ import annotations

import logging
import webbrowser
import urllib.parse
from typing import Optional

logger = logging.getLogger(__name__)

# ── Try to import DuckDuckGo search library ──
_HAS_DDGS = False
_DDGS_CLASS = None

try:
    from duckduckgo_search import DDGS
    _DDGS_CLASS = DDGS
    _HAS_DDGS = True
except ImportError:
    try:
        from ddgs import DDGS  # type: ignore
        _DDGS_CLASS = DDGS
        _HAS_DDGS = True
    except ImportError:
        logger.info("DuckDuckGo search library not available. Install: pip install duckduckgo-search")


class WebSearchEngine:
    """Web search engine using DuckDuckGo."""

    def search(self, query: str, max_results: int = 5) -> dict:
        """
        Search the web using DuckDuckGo.

        Returns a dict with:
        - results: list of {title, snippet, url}
        - summary: human-readable summary string
        - query: the original query
        """
        if not _HAS_DDGS or not _DDGS_CLASS:
            # Fallback: open browser search
            return self._browser_fallback(query)

        try:
            results = []
            with _DDGS_CLASS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", r.get("link", "")),
                    })

            if not results:
                return {
                    "results": [],
                    "summary": f"No results found for '{query}'",
                    "query": query,
                }

            # Build a human-readable summary
            summary_lines = [f"Here are the top results for '{query}':\n"]
            for i, r in enumerate(results, 1):
                summary_lines.append(f"{i}. **{r['title']}**")
                if r["snippet"]:
                    summary_lines.append(f"   {r['snippet'][:150]}")
                if r["url"]:
                    summary_lines.append(f"   🔗 {r['url']}")
                summary_lines.append("")

            logger.info(f"Web search for '{query}' returned {len(results)} results")
            return {
                "results": results,
                "summary": "\n".join(summary_lines),
                "query": query,
            }

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return self._browser_fallback(query, error=str(e))

    def search_news(self, query: str, max_results: int = 5) -> dict:
        """Search for news articles using DuckDuckGo."""
        if not _HAS_DDGS or not _DDGS_CLASS:
            return self._browser_fallback(query, search_type="news")

        try:
            results = []
            with _DDGS_CLASS() as ddgs:
                for r in ddgs.news(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("url", r.get("link", "")),
                        "source": r.get("source", ""),
                        "date": r.get("date", ""),
                    })

            summary_lines = [f"Latest news for '{query}':\n"]
            for i, r in enumerate(results, 1):
                summary_lines.append(f"{i}. **{r['title']}**")
                if r["source"]:
                    summary_lines.append(f"   Source: {r['source']}")
                if r["snippet"]:
                    summary_lines.append(f"   {r['snippet'][:150]}")
                summary_lines.append("")

            return {
                "results": results,
                "summary": "\n".join(summary_lines),
                "query": query,
            }

        except Exception as e:
            logger.error(f"News search failed: {e}")
            return self._browser_fallback(query, search_type="news", error=str(e))

    def open_in_browser(self, query: str) -> str:
        """Open a web search in the default browser."""
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(url)
        return f"Opened search for '{query}' in browser"

    def open_url(self, url: str) -> str:
        """Open a specific URL in the default browser."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened {url} in browser"

    def _browser_fallback(self, query: str, search_type: str = "web", error: Optional[str] = None) -> dict:
        """Fallback: open browser search when DDG library isn't available."""
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        if search_type == "news":
            url += "&tbm=nws"
        webbrowser.open(url)

        msg = f"Opened {search_type} search for '{query}' in browser"
        if error:
            msg = f"Search library error ({error}). {msg}"

        return {
            "results": [],
            "summary": msg,
            "query": query,
            "opened_in_browser": True,
        }


# Singleton
web_search_engine = WebSearchEngine()
