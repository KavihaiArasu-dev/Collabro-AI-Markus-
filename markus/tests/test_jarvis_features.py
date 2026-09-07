"""
Tests for Jarvis-style action modules and fast-path voice command routing.
"""

from config.constants import IntentType
from core.intent_classifier import intent_classifier
from core.voice_command_processor import VoiceCommandProcessor
from tools.tool_router import tool_router


def test_intent_types():
    assert IntentType.YOUTUBE == "youtube"
    assert IntentType.VOICE_COMMAND == "voice_command"


def test_voice_command_fast_path():
    processor = VoiceCommandProcessor()
    res = processor.try_execute("open chrome")
    assert res.matched is True
    assert res.action == "open_app"

    res_vol = processor.try_execute("volume up")
    assert res_vol.matched is True
    assert res_vol.action == "volume_up"

    res_unmatched = processor.try_execute("what is the theory of general relativity")
    assert res_unmatched.matched is False


def test_jarvis_tools_registered():
    tool_names = [t["name"] for t in tool_router.list_tools()]
    expected_tools = [
        "open_app", "close_app", "focus_app", "list_running_apps",
        "web_search", "web_search_news", "browser_open", "browser_search",
        "youtube_search", "youtube_play", "set_volume", "set_brightness",
        "take_screenshot", "lock_screen", "wifi_list", "get_battery",
        "get_network_info", "get_disk_info", "get_uptime", "get_system_summary",
    ]
    for tool in expected_tools:
        assert tool in tool_names, f"Missing tool: {tool}"
