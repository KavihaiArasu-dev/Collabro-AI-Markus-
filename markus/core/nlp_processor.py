"""
Markus AI — Natural Language Processing (NLP) & Intent Understanding Engine (§4, §15)

Provides deep multilingual natural language understanding for English, Tamil (தமிழ்),
and Tanglish/code-mixed speech and text. Extracts user intents, entity slots
(applications, queries, volume levels, files), and dispatches actions to the
verified execution subsystem.
"""

from __future__ import annotations

import difflib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from config.constants import IntentType
from core.verifier import verifier

logger = logging.getLogger(__name__)


@dataclass
class NLPCommandIntent:
    """Structured semantic intent representation produced by the NLP engine."""
    intent: IntentType
    action: str
    target: str = ""
    slots: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    language: str = "en"  # "en", "ta", "mixed"
    raw_text: str = ""


# ── TAMIL & MULTILINGUAL KNOWLEDGE DICTIONARIES ──

# App name normalization (maps Tamil transliterations, aliases, and common typos to canonical app names)
APP_CANONICAL_MAP: Dict[str, str] = {
    # Browsers
    "chrome": "chrome",
    "குரோம்": "chrome",
    "கூகுள் குரோம்": "chrome",
    "firefox": "firefox",
    "பயர்பாக்ஸ்": "firefox",
    "edge": "edge",
    "எட்ஜ்": "edge",
    "brave": "brave",
    "பிரேவ்": "brave",
    "opera": "opera",
    "ஒபேரா": "opera",

    # Editors & IDEs
    "vscode": "code",
    "vs code": "code",
    "code": "code",
    "விஸ்கோடு": "code",
    "visual studio": "devenv",
    "notepad": "notepad",
    "நோட்பேட்": "notepad",
    "sublime": "sublime_text",

    # Terminals
    "terminal": "wt",
    "டெர்மினல்": "wt",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "பவர்ஷெல்": "powershell",

    # Media & Communication
    "youtube": "youtube",
    "யூடியூப்": "youtube",
    "யூட்யூப்": "youtube",
    "spotify": "spotify",
    "ஸ்பாட்டிஃபை": "spotify",
    "vlc": "vlc",
    "விஎல்சி": "vlc",
    "whatsapp": "whatsapp",
    "வாட்ஸ்அப்": "whatsapp",
    "வாட்சப்": "whatsapp",
    "telegram": "telegram",
    "டெலிகிராம்": "telegram",
    "discord": "discord",
    "டிஸ்கார்ட்": "discord",
    "slack": "slack",
    "ஸ்லாக்": "slack",
    "zoom": "zoom",
    "ஜூம்": "zoom",
    "teams": "teams",
    "டீம்ஸ்": "teams",

    # Web services & AI
    "google": "google",
    "கூகுள்": "google",
    "github": "github",
    "கிட்ஹப்": "github",
    "chatgpt": "chatgpt",
    "சாட்ஜிபிடி": "chatgpt",

    # System utilities
    "calculator": "calc",
    "கல்குலேட்டர்": "calc",
    "கணிப்பான்": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "பெயிண்ட்": "mspaint",
    "explorer": "explorer",
    "எக்ஸ்ப்ளோரர்": "explorer",
    "கோப்பு மேலாளர்": "explorer",
    "file explorer": "explorer",
    "task manager": "taskmgr",
    "டாஸ்க் மேனேஜர்": "taskmgr",
    "settings": "ms-settings:",
    "அமைப்புகள்": "ms-settings:",
}

# Tamil suffix patterns to peel off object words (e.g., chrome-ஐ -> chrome, youtube-ல -> youtube)
TAMIL_SUFFIXES = [
    r"[-_]?(?:ஐ|ai)$",               # Accusative: chrome-ஐ / chromai
    r"[-_]?(?:இல்|il|ல்|la|ல)$",      # Locative: youtube-ல் / youtubela
    r"[-_]?(?:க்கு|kku|ku)$",        # Dative: google-க்கு / googleku
    r"[-_]?(?:உடன்|udan|ோடு|ode)$",  # Associative
    r"[-_]?(?:ஆல்|aal)$",            # Instrumental
]


class NLPProcessor:
    """
    Multilingual Natural Language Processor for intent detection,
    slot filling, and semantic computer-use automation.
    """

    def __init__(self):
        self._compiled_suffixes = [re.compile(p, re.IGNORECASE) for p in TAMIL_SUFFIXES]

    def detect_language(self, text: str) -> str:
        """Detect whether text contains Tamil script, English, or code-mixed/Tanglish."""
        has_tamil = bool(re.search(r"[\u0B80-\u0BFF]", text))
        has_latin = bool(re.search(r"[a-zA-Z]", text))

        if has_tamil and has_latin:
            return "mixed"
        if has_tamil:
            return "ta"

        # Check for romanized Tanglish markers
        tanglish_markers = {
            "pannu", "panu", "podu", "sei", "paru", "kodu", "eduda", "sollu",
            "irukku", "koodu", "koottu", "kurai", "thira", "moodu", "nillu"
        }
        tokens = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
        if tokens & tanglish_markers:
            return "mixed"

        return "en"

    def strip_tamil_morphology(self, word: str) -> str:
        """Strip grammatical suffixes from a token (e.g. 'chrome-ஐ' -> 'chrome')."""
        clean_word = word.strip()
        for pat in self._compiled_suffixes:
            clean_word = pat.sub("", clean_word)
        return clean_word.strip()

    def normalize_text(self, text: str) -> str:
        """Lowercase, strip excessive punctuation, and normalize whitespace."""
        if not text:
            return ""
        # Preserve Tamil and alphanumeric tokens, replace special symbols with spaces
        cleaned = re.sub(r"[,;!\"'’‘“”()[\]{}*#]+", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
        return cleaned

    def extract_app_target(self, text: str) -> Optional[str]:
        """Extract and normalize target desktop application from text in English or Tamil."""
        normalized = self.normalize_text(text)
        tokens = normalized.split()

        # Check multi-word app names first
        for key, canonical in APP_CANONICAL_MAP.items():
            if " " in key and key in normalized:
                return canonical

        # Check token-by-token with suffix peeling
        for tok in tokens:
            peeled = self.strip_tamil_morphology(tok)
            if peeled in APP_CANONICAL_MAP:
                return APP_CANONICAL_MAP[peeled]
            if tok in APP_CANONICAL_MAP:
                return APP_CANONICAL_MAP[tok]

        # Fuzzy match across dictionary for typos
        for tok in tokens:
            peeled = self.strip_tamil_morphology(tok)
            matches = difflib.get_close_matches(peeled, APP_CANONICAL_MAP.keys(), n=1, cutoff=0.82)
            if matches:
                return APP_CANONICAL_MAP[matches[0]]

        return None

    def parse_intent(self, text: str) -> NLPCommandIntent:
        """
        Deep multilingual semantic parsing of user command.
        Identifies action, entity targets, and confidence score.
        """
        raw = text.strip()
        lang = self.detect_language(raw)
        norm = self.normalize_text(raw)

        # ── 1. SCREENSHOT INTENT ──
        # English: take screenshot, capture screen, screen grab, take a snap
        # Tamil: ஸ்கிரீன்ஷாட் எடு, திரையை படம் பிடி, ஸ்கிரீன்ஷாட் போடு
        if any(term in norm for term in [
            "screenshot", "screen shot", "screen grab", "capture screen", "snap screen",
            "ஸ்கிரீன்ஷாட்", "ஸ்கிரீன் ஷாட்", "திரைப்படம்", "ஸ்கிரீன்சாட்", "ஸ்கிரீன்"
        ]) and any(action in norm for term in ["எடு", "பிடி", "போடு", "take", "capture", "grab", "shoot", "செய்"] for action in [term]):
            return NLPCommandIntent(
                intent=IntentType.SYSTEM_CONTROL,
                action="screenshot",
                confidence=0.98,
                language=lang,
                raw_text=raw,
            )
        # Direct one-word screenshot command
        if norm in ["screenshot", "screen shot", "ஸ்கிரீன்ஷாட்", "take a screenshot"]:
            return NLPCommandIntent(
                intent=IntentType.SYSTEM_CONTROL,
                action="screenshot",
                confidence=0.99,
                language=lang,
                raw_text=raw,
            )

        # ── 2. VOLUME / SOUND CONTROL ──
        # English: mute, unmute, volume up, volume down, set volume to 50
        # Tamil: மியூட் செய், சத்தம் குறை, வால்யூம் கூட்டு, சத்தத்தை கூட்டு
        is_vol_context = any(w in norm for w in [
            "volume", "sound", "audio", "mute", "unmute",
            "வால்யூம்", "சத்தம்", "ஒலி", "மியூட்", "அன்மியூட்"
        ])

        if is_vol_context:
            # Mute
            if any(w in norm for w in ["mute", "quiet", "silent", "மியூட்", "அமைதி", "ஒலியடக்கு"]):
                return NLPCommandIntent(
                    intent=IntentType.SYSTEM_CONTROL,
                    action="volume_mute",
                    confidence=0.95,
                    language=lang,
                    raw_text=raw,
                )
            # Unmute
            if any(w in norm for w in ["unmute", "அன்மியூட்", "ஒலியை இயக்கு"]):
                return NLPCommandIntent(
                    intent=IntentType.SYSTEM_CONTROL,
                    action="volume_unmute",
                    confidence=0.95,
                    language=lang,
                    raw_text=raw,
                )
            # Volume Up
            if any(w in norm for w in ["up", "increase", "raise", "louder", "கூட்டு", "அதிகரி", "ஏற்று", "koottu"]):
                return NLPCommandIntent(
                    intent=IntentType.SYSTEM_CONTROL,
                    action="volume_up",
                    confidence=0.94,
                    language=lang,
                    raw_text=raw,
                )
            # Volume Down
            if any(w in norm for w in ["down", "decrease", "lower", "quieter", "softer", "குறை", "இருக்கு", "kurai"]):
                return NLPCommandIntent(
                    intent=IntentType.SYSTEM_CONTROL,
                    action="volume_down",
                    confidence=0.94,
                    language=lang,
                    raw_text=raw,
                )
            # Volume Set (e.g. volume 60, set volume to 50, வால்யூம் 70)
            level_match = re.search(r"\b(\d{1,3})\s*%?", norm)
            if level_match:
                level_val = min(100, max(0, int(level_match.group(1))))
                return NLPCommandIntent(
                    intent=IntentType.SYSTEM_CONTROL,
                    action="volume_set",
                    target=str(level_val),
                    slots={"level": level_val},
                    confidence=0.96,
                    language=lang,
                    raw_text=raw,
                )

        # ── 3. APPLICATION CONTROL (OPEN / CLOSE / FOCUS) ──
        target_app = self.extract_app_target(norm)

        # Open action verbs:
        # English: open, launch, start, run, bring up
        # Tamil: திற, திறக்கவும், தொடங்கு, ஓபன், ஆரம்பி, open pannu
        is_open_action = any(v in norm for v in [
            "open", "launch", "start", "run",
            "திற", "திறக்க", "தொடங்கு", "ஆரம்பி", "ஓபன்"
        ]) or norm.endswith("open pannu") or norm.endswith("open sei")

        # Close action verbs:
        # English: close, quit, exit, terminate, kill, stop
        # Tamil: மூடு, மூடவும், நிறுத்து, குளோஸ், அழி, close pannu
        is_close_action = any(v in norm for v in [
            "close", "quit", "exit", "terminate", "kill", "stop",
            "மூடு", "மூடவும்", "நிறுத்து", "குளோஸ்"
        ]) or norm.endswith("close pannu")

        if target_app and is_open_action:
            return NLPCommandIntent(
                intent=IntentType.APP_CONTROL,
                action="open_app",
                target=target_app,
                slots={"app": target_app},
                confidence=0.95,
                language=lang,
                raw_text=raw,
            )

        if target_app and is_close_action:
            return NLPCommandIntent(
                intent=IntentType.APP_CONTROL,
                action="close_app",
                target=target_app,
                slots={"app": target_app},
                confidence=0.95,
                language=lang,
                raw_text=raw,
            )

        # ── 4. YOUTUBE / MEDIA PLAYBACK ──
        # English: play song on youtube, play bohemian rhapsody
        # Tamil: யூடியூபில் பாடல் போடு, பாட்டு இயக்கு, பாட்டு போடு
        is_media = any(w in norm for w in [
            "youtube", "song", "music", "play", "track",
            "யூடியூப்", "யூடியூபில்", "பாட்டு", "பாடல்", "இசை", "இயக்கு", "போடு"
        ])
        if is_media and ("play" in norm or "போடு" in norm or "இயக்கு" in norm or "கேள்" in norm or "youtube" in norm or "யூடியூப்" in norm):
            # Clean query from trigger words
            query = norm
            for trigger in [
                "play", "on youtube", "in youtube", "song", "music", "video",
                "யூடியூபில்", "யூடியூப்ல", "யூடியூப்", "பாட்டு", "பாடல்", "போடு", "இயக்கு", "ப்ளே"
            ]:
                query = query.replace(trigger, " ")
            query = re.sub(r"\s+", " ", query).strip()
            if not query:
                query = "top trending music"

            return NLPCommandIntent(
                intent=IntentType.YOUTUBE,
                action="youtube_play",
                target=query,
                slots={"query": query},
                confidence=0.92,
                language=lang,
                raw_text=raw,
            )

        # ── 5. WEB SEARCH ──
        # English: search for X, google X, find online X
        # Tamil: கூகிளில் தேடு, இணையத்தில் தேடு, தேடவும், கண்டுபிடி
        is_search = any(w in norm for w in [
            "search for", "search", "google", "look up",
            "தேடு", "தேடவும்", "கண்டுபிடி", "தேடல்", "இணையத்தில்"
        ])
        if is_search:
            clean_q = norm
            for s_word in [
                "search for", "search about", "search", "google", "look up", "find online",
                "இணையத்தில் தேடு", "கூகிளில் தேடு", "தேடவும்", "தேடு", "கண்டுபிடி"
            ]:
                clean_q = clean_q.replace(s_word, " ")
            clean_q = re.sub(r"\s+", " ", clean_q).strip()
            if clean_q:
                return NLPCommandIntent(
                    intent=IntentType.SEARCH,
                    action="web_search",
                    target=clean_q,
                    slots={"query": clean_q},
                    confidence=0.91,
                    language=lang,
                    raw_text=raw,
                )

        # ── 6. LOCK SCREEN & SYSTEM TELEMETRY ──
        if any(w in norm for w in ["lock screen", "lock the pc", "lock computer", "லாக் செய்", "பூட்டு"]):
            return NLPCommandIntent(
                intent=IntentType.SYSTEM_CONTROL,
                action="lock_screen",
                confidence=0.97,
                language=lang,
                raw_text=raw,
            )

        if any(w in norm for w in [
            "battery", "பேட்டரி", "பேட்டரி அளவு", "how much battery"
        ]):
            return NLPCommandIntent(
                intent=IntentType.SYSTEM_CONTROL,
                action="battery",
                confidence=0.95,
                language=lang,
                raw_text=raw,
            )

        if any(w in norm for w in [
            "system status", "system info", "கணினி நிலை", "சிபிசி", "cpu usage", "ram usage"
        ]):
            return NLPCommandIntent(
                intent=IntentType.SYSTEM_CONTROL,
                action="system_info",
                confidence=0.95,
                language=lang,
                raw_text=raw,
            )

        # ── 7. CODE & COGNITIVE QUERIES ──
        if any(w in norm for w in [
            "code", "program", "function", "script", "algorithm", "fix bug", "debug",
            "குறிமுறை", "நிரல்", "செயல்திட்டம்", "கோட்"
        ]):
            return NLPCommandIntent(
                intent=IntentType.CODE,
                action="code_generation",
                confidence=0.88,
                language=lang,
                raw_text=raw,
            )

        # Fallback to general conversational chat or question
        return NLPCommandIntent(
            intent=IntentType.QUESTION if "?" in raw or any(w in norm for w in ["what", "how", "who", "why", "என்ன", "எப்படி", "யார்", "ஏன்"]) else IntentType.CHAT,
            action="chat",
            confidence=0.60,
            language=lang,
            raw_text=raw,
        )

    def process_and_execute(self, text: str) -> Optional[Any]:
        """
        End-to-end NLP processing: Parse natural input, resolve entities,
        and directly dispatch to desktop automation with closed-loop verification.
        """
        parsed = self.parse_intent(text)
        if parsed.confidence < 0.70:
            return None

        # Import action engines lazily
        try:
            from actions.app_controller import app_controller
            from actions.system_settings import system_settings
            from actions.youtube_controller import youtube_controller
            from actions.web_search import web_search_engine
            from actions.system_monitor import system_monitor
            from core.voice_command_processor import VoiceCommandResult
        except ImportError as e:
            logger.error(f"NLP execution dependency error: {e}")
            return None

        action = parsed.action

        # 1. App Control
        if action == "open_app" and parsed.target:
            result = app_controller.open_app(parsed.target)
            ver = verifier.verify_process_running(parsed.target, timeout=2.0)
            status_msg = f"{result} [Verified: {ver.details}]" if ver.verified else f"{result} [Warning: {ver.details}]"
            return VoiceCommandResult(
                matched=True,
                command_type="app_control",
                action=action,
                response=status_msg,
                verified=ver.verified,
                data=ver.to_dict(),
            )

        if action == "close_app" and parsed.target:
            result = app_controller.close_app(parsed.target)
            ver = verifier.verify_process_terminated(parsed.target, timeout=2.0)
            status_msg = f"{result} [Verified: {ver.details}]" if ver.verified else f"{result} [Warning: {ver.details}]"
            return VoiceCommandResult(
                matched=True,
                command_type="app_control",
                action=action,
                response=status_msg,
                verified=ver.verified,
                data=ver.to_dict(),
            )

        # 2. Screenshot
        if action == "screenshot":
            result = system_settings.take_screenshot()
            verified = False
            data = None
            if "saved to " in result:
                path = result.split("saved to ")[-1].strip()
                ver = verifier.verify_file_exists(path, min_size=100)
                verified = ver.verified
                data = ver.to_dict()
            return VoiceCommandResult(
                matched=True,
                command_type="system",
                action=action,
                response=result,
                verified=verified,
                data=data,
            )

        # 3. Volume
        if action == "volume_mute":
            result = system_settings.set_volume("mute")
            return VoiceCommandResult(matched=True, command_type="system", action=action, response=result, verified=True)
        if action == "volume_unmute":
            result = system_settings.set_volume("unmute")
            return VoiceCommandResult(matched=True, command_type="system", action=action, response=result, verified=True)
        if action == "volume_up":
            result = system_settings.set_volume("up")
            return VoiceCommandResult(matched=True, command_type="system", action=action, response=result, verified=True)
        if action == "volume_down":
            result = system_settings.set_volume("down")
            return VoiceCommandResult(matched=True, command_type="system", action=action, response=result, verified=True)
        if action == "volume_set" and "level" in parsed.slots:
            result = system_settings.set_volume("set", parsed.slots["level"])
            return VoiceCommandResult(matched=True, command_type="system", action=action, response=result, verified=True)

        # 4. YouTube
        if action == "youtube_play" and parsed.target:
            result = youtube_controller.play(parsed.target)
            return VoiceCommandResult(matched=True, command_type="media", action=action, response=result, verified=True)

        # 5. Web Search
        if action == "web_search" and parsed.target:
            search_res = web_search_engine.search(parsed.target)
            summary = search_res.get("summary", f"Searched for {parsed.target}")
            return VoiceCommandResult(
                matched=True,
                command_type="search",
                action=action,
                response=summary,
                data=search_res,
                verified=True,
            )

        # 6. Lock Screen
        if action == "lock_screen":
            result = system_settings.lock_screen()
            return VoiceCommandResult(matched=True, command_type="system", action=action, response=result, verified=True)

        # 7. System Info & Battery
        if action == "battery":
            bat = system_monitor.get_battery()
            res = f"Battery: {bat.get('percent', 'unknown')}% ({'charging' if bat.get('charging') else 'on battery'})"
            return VoiceCommandResult(matched=True, command_type="system", action=action, response=res, data=bat, verified=True)

        if action == "system_info":
            info = system_monitor.get_system_info()
            res = f"CPU: {info.get('cpu_percent', 0)}%, RAM: {info.get('memory_used_gb', info.get('ram_used_gb', 0))}/{info.get('memory_total_gb', info.get('ram_total_gb', 0))}GB"
            return VoiceCommandResult(matched=True, command_type="system", action=action, response=res, data=info, verified=True)

        return None


# Singleton instance
nlp_processor = NLPProcessor()
