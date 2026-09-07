"""
Markus AI — Actions Module

Desktop automation actions inspired by Jarvis:
- App control (open, close, focus)
- Web search (DuckDuckGo)
- YouTube search & play
- System settings (volume, brightness, screenshot)
- System monitoring (battery, network, uptime)
"""

from actions.app_controller import app_controller
from actions.web_search import web_search_engine
from actions.youtube_controller import youtube_controller
from actions.system_settings import system_settings
from actions.system_monitor import system_monitor

__all__ = [
    "app_controller",
    "web_search_engine",
    "youtube_controller",
    "system_settings",
    "system_monitor",
]
