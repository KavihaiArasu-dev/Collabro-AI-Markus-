"""
Markus AI — Voice Command Processor (§15, Phase 4)

A fast-path processor that parses voice commands and maps them directly
to tool calls, bypassing the LLM for instant execution.

Examples:
- "Open Chrome"              → app_controller.open_app("chrome")
- "Close Spotify"            → app_controller.close_app("spotify")
- "Volume up"                → system_settings.set_volume("up")
- "Mute"                     → system_settings.set_volume("mute")
- "Take a screenshot"        → system_settings.take_screenshot()
- "Play Blinding Lights"     → youtube_controller.play("Blinding Lights")
- "Search for Python tutorials" → web_search_engine.search("Python tutorials")
- "What's the battery level?" → system_monitor.get_battery()
- "Open google.com"          → web_search_engine.open_url("google.com")
"""

from __future__ import annotations

import difflib
import logging
import re
from dataclasses import dataclass
from typing import Optional, Callable, Any

from core.verifier import verifier

logger = logging.getLogger(__name__)


@dataclass
class VoiceCommandResult:
    """Result of a voice command execution."""
    matched: bool
    command_type: str = ""
    action: str = ""
    response: str = ""
    data: Optional[dict] = None
    verified: bool = False


# ── Pre-compiled command patterns ──
# Order matters: more specific patterns should come first

_COMMAND_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # App Control — Open
    (re.compile(r"^(?:open|launch|start|run)\s+(.+?)(?:\s+app)?$", re.I), "open_app", "app_control"),
    # App Control — Close
    (re.compile(r"^(?:close|quit|exit|kill|stop|terminate)\s+(.+?)(?:\s+app)?$", re.I), "close_app", "app_control"),
    # App Control — Focus
    (re.compile(r"^(?:focus|switch to|go to|show)\s+(.+?)(?:\s+app)?$", re.I), "focus_app", "app_control"),

    # Volume — Mute/Unmute
    (re.compile(r"^(?:mute|mute (?:the )?(?:volume|sound|audio))$", re.I), "volume_mute", "system_settings"),
    (re.compile(r"^(?:unmute|unmute (?:the )?(?:volume|sound|audio))$", re.I), "volume_unmute", "system_settings"),
    # Volume — Up/Down
    (re.compile(r"^(?:volume up|increase volume|turn up (?:the )?volume|louder)$", re.I), "volume_up", "system_settings"),
    (re.compile(r"^(?:volume down|decrease volume|turn down (?:the )?volume|quieter|softer)$", re.I), "volume_down", "system_settings"),
    # Volume — Set
    (re.compile(r"^(?:set )?volume (?:to )?(\d+)(?:\s*%)?$", re.I), "volume_set", "system_settings"),

    # Brightness
    (re.compile(r"^(?:brightness up|increase brightness|brighter)$", re.I), "brightness_up", "system_settings"),
    (re.compile(r"^(?:brightness down|decrease brightness|dimmer|darker)$", re.I), "brightness_down", "system_settings"),
    (re.compile(r"^(?:set )?brightness (?:to )?(\d+)(?:\s*%)?$", re.I), "brightness_set", "system_settings"),

    # Screenshot
    (re.compile(r"^(?:take (?:a )?)?screenshot$", re.I), "screenshot", "system_settings"),
    (re.compile(r"^(?:capture|grab) (?:the )?screen$", re.I), "screenshot", "system_settings"),

    # Lock screen
    (re.compile(r"^lock (?:the )?(?:screen|computer|pc)$", re.I), "lock_screen", "system_settings"),

    # YouTube — Open
    (re.compile(r"^(?:open|launch|go to)\s+(?:youtube|yt)$", re.I), "youtube_open", "youtube"),
    # YouTube — Play
    (re.compile(r"^(?:play|play me)\s+(.+?)(?:\s+on youtube)?$", re.I), "youtube_play", "youtube"),
    (re.compile(r"^(?:youtube|yt)\s+play\s+(.+)$", re.I), "youtube_play", "youtube"),
    (re.compile(r"^play\s+(.+)\s+(?:on youtube|on yt)$", re.I), "youtube_play", "youtube"),
    # YouTube — Search
    (re.compile(r"^(?:search youtube|youtube search|search on youtube|search yt)\s+(?:for\s+)?(.+)$", re.I), "youtube_search", "youtube"),

    # Web Search
    (re.compile(r"^(?:search|search for|search the web for|google|look up|find online)\s+(.+)$", re.I), "web_search", "search"),
    (re.compile(r"^(?:search|find)\s+(.+?)\s+(?:on the web|online|on google|on internet)$", re.I), "web_search", "search"),
    # News search
    (re.compile(r"^(?:news about|latest news on|what's (?:the )?news (?:about|on))\s+(.+)$", re.I), "news_search", "search"),

    # Open website/URL
    (re.compile(r"^(?:open|go to|navigate to|visit)\s+((?:https?://)?[\w.-]+\.[\w]{2,}(?:/\S*)?)$", re.I), "open_url", "browser"),

    # System Info
    (re.compile(r"^(?:what(?:'s| is) (?:my |the )?battery(?:\s+level)?|battery status|battery level|how much battery).*$", re.I), "battery", "system"),
    (re.compile(r"^(?:what(?:'s| is) (?:my |the )?network|network status|am i connected|internet status).*$", re.I), "network", "system"),
    (re.compile(r"^(?:system (?:status|info|information)|what(?:'s| is) (?:my |the )?system status)$", re.I), "system_info", "system"),
    (re.compile(r"^(?:uptime|system uptime|how long has (?:my |the )?(?:computer|system|pc) been (?:on|running)).*$", re.I), "uptime", "system"),
    (re.compile(r"^(?:what(?:'s| is) (?:my |the )?(?:cpu|processor) usage|cpu (?:status|usage))$", re.I), "system_info", "system"),
    (re.compile(r"^(?:what(?:'s| is) (?:my |the )?(?:ram|memory) usage|ram (?:status|usage)|memory usage)$", re.I), "system_info", "system"),
    (re.compile(r"^(?:list|show|what are) (?:the )?(?:running )?(?:apps|applications|programs|processes)$", re.I), "list_apps", "system"),

    # Power management
    (re.compile(r"^(?:shutdown|shut down|power off) (?:the )?(?:computer|system|pc)$", re.I), "shutdown", "power"),
    (re.compile(r"^(?:restart|reboot) (?:the )?(?:computer|system|pc)$", re.I), "restart", "power"),
]


class VoiceCommandProcessor:
    """
    Fast-path voice command processor.

    Parses natural-language commands and maps them directly to action
    module calls, bypassing the LLM for near-instant execution.
    """

    def __init__(self):
        # Lazy-import action modules to avoid circular imports
        self._app_controller: Any = None
        self._web_search: Any = None
        self._youtube: Any = None
        self._system_settings: Any = None
        self._system_monitor: Any = None

    def _ensure_modules(self):
        """Lazily import action modules."""
        if self._app_controller is None:
            from actions.app_controller import app_controller
            from actions.web_search import web_search_engine
            from actions.youtube_controller import youtube_controller
            from actions.system_settings import system_settings
            from actions.system_monitor import system_monitor

            self._app_controller = app_controller
            self._web_search = web_search_engine
            self._youtube = youtube_controller
            self._system_settings = system_settings
            self._system_monitor = system_monitor

    def try_execute(self, text: str) -> VoiceCommandResult:
        """
        Try to match and execute a voice command.

        Returns VoiceCommandResult with matched=True if the command was
        recognized and executed, or matched=False if it should be routed
        to the LLM instead.
        """
        if not text or not text.strip():
            return VoiceCommandResult(matched=False)

        clean = text.strip()

        # 1. Try fast-path regex patterns first
        for pattern, action, cmd_type in _COMMAND_PATTERNS:
            match = pattern.match(clean)
            if match:
                return self._dispatch(action, cmd_type, match)

        # 2. Escalate to Multilingual NLP Engine (Tamil, Tanglish, and natural phrasing)
        try:
            from core.nlp_processor import nlp_processor
            nlp_res = nlp_processor.process_and_execute(clean)
            if nlp_res is not None:
                return nlp_res
        except Exception as nlp_err:
            logger.debug(f"NLP processing fallback notice: {nlp_err}")

        return VoiceCommandResult(matched=False)

    def _dispatch(self, action: str, cmd_type: str, match: re.Match) -> VoiceCommandResult:
        """Execute a matched command."""
        self._ensure_modules()

        try:
            groups = match.groups()
            arg = groups[0].strip() if groups else ""

            # ── App Control ──
            if action == "open_app":
                result = self._app_controller.open_app(arg)
                ver = verifier.verify_process_running(arg, timeout=2.0)
                status_msg = f"{result} [Verified: {ver.details}]" if ver.verified else f"{result} [Warning: {ver.details}]"
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=status_msg, verified=ver.verified, data=ver.to_dict())
            elif action == "close_app":
                result = self._app_controller.close_app(arg)
                ver = verifier.verify_process_terminated(arg, timeout=2.0)
                status_msg = f"{result} [Verified: {ver.details}]" if ver.verified else f"{result} [Warning: {ver.details}]"
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=status_msg, verified=ver.verified, data=ver.to_dict())
            elif action == "focus_app":
                result = self._app_controller.focus_app(arg)
                ver = verifier.verify_window_focused(arg, timeout=2.0)
                status_msg = f"{result} [Verified: {ver.details}]" if ver.verified else f"{result} [Warning: {ver.details}]"
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=status_msg, verified=ver.verified, data=ver.to_dict())

            # ── Volume ──
            elif action == "volume_mute":
                result = self._system_settings.set_volume("mute")
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)
            elif action == "volume_unmute":
                result = self._system_settings.set_volume("unmute")
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)
            elif action == "volume_up":
                result = self._system_settings.set_volume("up")
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)
            elif action == "volume_down":
                result = self._system_settings.set_volume("down")
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)
            elif action == "volume_set":
                result = self._system_settings.set_volume("set", int(arg))
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)

            # ── Brightness ──
            elif action == "brightness_up":
                result = self._system_settings.set_brightness("up")
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)
            elif action == "brightness_down":
                result = self._system_settings.set_brightness("down")
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)
            elif action == "brightness_set":
                result = self._system_settings.set_brightness("set", int(arg))
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)

            # ── Screenshot ──
            elif action == "screenshot":
                result = self._system_settings.take_screenshot()
                verified = False
                data = None
                if "saved to " in result:
                    path = result.split("saved to ")[-1].strip()
                    ver = verifier.verify_file_exists(path, min_size=100)
                    verified = ver.verified
                    data = ver.to_dict()
                return VoiceCommandResult(
                    matched=True, command_type=cmd_type, action=action, response=result, verified=verified, data=data
                )

            # ── Lock Screen ──
            elif action == "lock_screen":
                result = self._system_settings.lock_screen()
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)

            # ── YouTube ──
            elif action == "youtube_open":
                import webbrowser
                webbrowser.open("https://www.youtube.com")
                ver = verifier.verify_process_running("youtube", timeout=2.0)
                status_msg = f"Opened YouTube in browser [Verified: {ver.details}]" if ver.verified else "Opened YouTube in browser"
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=status_msg, verified=ver.verified, data=ver.to_dict())
            elif action == "youtube_play":
                result = self._youtube.play(arg)
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result, verified=True)
            elif action == "youtube_search":
                data = self._youtube.search(arg)
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=data.get("summary", ""), data=data)

            # ── Web Search ──
            elif action == "web_search":
                data = self._web_search.search(arg)
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=data.get("summary", ""), data=data)
            elif action == "news_search":
                data = self._web_search.search_news(arg)
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=data.get("summary", ""), data=data)

            # ── Open URL ──
            elif action == "open_url":
                result = self._web_search.open_url(arg)
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)

            # ── System Info ──
            elif action == "battery":
                data = self._system_monitor.get_battery()
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=data.get("summary", str(data)), data=data)
            elif action == "network":
                data = self._system_monitor.get_network_info()
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=data.get("summary", str(data)), data=data)
            elif action == "system_info":
                summary = self._system_monitor.get_summary()
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=summary)
            elif action == "uptime":
                result = self._system_monitor.get_uptime()
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=result)
            elif action == "list_apps":
                apps = self._app_controller.list_running_apps()
                summary = "Running applications:\n" + "\n".join(
                    f"  • {a['name']} (CPU: {a['cpu_percent']}%, RAM: {a['memory_percent']}%)"
                    for a in apps[:15]
                )
                return VoiceCommandResult(matched=True, command_type=cmd_type, action=action, response=summary, data={"apps": apps})

            # ── Power ──
            elif action == "shutdown":
                return VoiceCommandResult(
                    matched=True, command_type=cmd_type, action=action,
                    response="⚠️ Shutdown requested. This requires confirmation.",
                    data={"requires_confirmation": True, "tool": "shutdown"},
                )
            elif action == "restart":
                return VoiceCommandResult(
                    matched=True, command_type=cmd_type, action=action,
                    response="⚠️ Restart requested. This requires confirmation.",
                    data={"requires_confirmation": True, "tool": "restart"},
                )

            return VoiceCommandResult(matched=False)

        except Exception as e:
            logger.error(f"Voice command execution error: {e}")
            return VoiceCommandResult(
                matched=True, command_type=cmd_type, action=action,
                response=f"Command failed: {e}",
            )


# Singleton
voice_command_processor = VoiceCommandProcessor()
