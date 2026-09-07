"""
Markus AI — App Controller (inspired by Jarvis open_app.py)

Cross-platform application launcher and closer with 30+ app aliases.
Supports Windows, macOS, and Linux with intelligent fallbacks:
- Windows: os.startfile → PowerShell Start-Process → Start Menu search
- macOS: open -a
- Linux: subprocess

Features:
- Open apps by friendly name ("chrome", "vscode", "spotify")
- Close apps by process name (graceful termination via psutil)
- Focus an already-running app window
- List running user applications
"""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Optional

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

logger = logging.getLogger(__name__)

_SYSTEM = platform.system()

# ── Web Application & Website Target Registry ──
_WEB_TARGETS: dict[str, str] = {
    # Video & Media
    "youtube": "https://www.youtube.com",
    "yt": "https://www.youtube.com",
    "netflix": "https://www.netflix.com",
    "prime video": "https://www.primevideo.com",
    "hotstar": "https://www.hotstar.com",
    "disney+": "https://www.disneyplus.com",
    "spotify web": "https://open.spotify.com",
    "twitch": "https://www.twitch.tv",

    # Search & AI
    "google": "https://www.google.com",
    "bing": "https://www.bing.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com",
    "perplexity": "https://www.perplexity.ai",
    "duckduckgo": "https://duckduckgo.com",

    # Developer & Cloud
    "github": "https://github.com",
    "gitlab": "https://gitlab.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "huggingface": "https://huggingface.co",
    "aws": "https://aws.amazon.com",
    "azure": "https://portal.azure.com",

    # Social & Community
    "twitter": "https://x.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "threads": "https://www.threads.net",

    # Workspace & Productivity
    "gmail": "https://mail.google.com",
    "google mail": "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com",
    "sheets": "https://sheets.google.com",
    "google maps": "https://maps.google.com",
    "maps": "https://maps.google.com",
    "notion": "https://www.notion.so",
    "canva": "https://www.canva.com",
    "whatsapp web": "https://web.whatsapp.com",

    # Shopping & Reference
    "amazon": "https://www.amazon.com",
    "flipkart": "https://www.flipkart.com",
    "wikipedia": "https://www.wikipedia.org",
}

_DYNAMIC_WEB_TARGETS: Optional[dict[str, str]] = None


def _load_dynamic_web_targets() -> dict[str, str]:
    """Lazy load dynamic website catalog from action_targets.json if available."""
    global _DYNAMIC_WEB_TARGETS
    if _DYNAMIC_WEB_TARGETS is not None:
        return _DYNAMIC_WEB_TARGETS

    _DYNAMIC_WEB_TARGETS = dict(_WEB_TARGETS)
    try:
        data_path = Path(__file__).resolve().parent.parent / "data" / "action_targets.json"
        if data_path.is_file():
            import json
            with open(data_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
                for key, item in catalog.items():
                    if isinstance(item, dict) and item.get("type") == "website" and item.get("url"):
                        url = item["url"]
                        _DYNAMIC_WEB_TARGETS[key.lower().strip()] = url
                        for alias in item.get("aliases", []):
                            _DYNAMIC_WEB_TARGETS[alias.lower().strip()] = url
    except Exception as e:
        logger.debug(f"Action catalog load notice: {e}")

    return _DYNAMIC_WEB_TARGETS


def get_web_target_url(name: str) -> Optional[str]:
    """Check if name corresponds to a known web target, website, or direct URL."""
    clean = name.lower().strip()
    if clean.startswith("http://") or clean.startswith("https://"):
        return name

    clean = re.sub(r"^(?:the|open)\s+", "", clean).strip()
    targets = _load_dynamic_web_targets()
    if clean in targets:
        return targets[clean]

    if re.match(r"^[\w.-]+\.(?:com|org|net|io|ai|dev|co|in|edu|gov|app)(?:/\S*)?$", clean):
        return f"https://{clean}"

    return None


# ── Application Alias Map ──
# Maps friendly names to platform-specific executable names/identifiers
_APP_ALIASES: dict[str, dict[str, str]] = {
    # Browsers
    "chrome":             {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "google chrome":      {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "firefox":            {"Windows": "firefox",                 "Darwin": "Firefox",              "Linux": "firefox"},
    "edge":               {"Windows": "msedge",                  "Darwin": "Microsoft Edge",       "Linux": "microsoft-edge"},
    "microsoft edge":     {"Windows": "msedge",                  "Darwin": "Microsoft Edge",       "Linux": "microsoft-edge"},
    "brave":              {"Windows": "brave",                   "Darwin": "Brave Browser",        "Linux": "brave-browser"},
    "opera":              {"Windows": "opera",                   "Darwin": "Opera",                "Linux": "opera"},
    "safari":             {"Windows": "msedge",                  "Darwin": "Safari",               "Linux": "firefox"},

    # Communication
    "whatsapp":           {"Windows": "WhatsApp",                "Darwin": "WhatsApp",             "Linux": "whatsapp"},
    "telegram":           {"Windows": "Telegram",                "Darwin": "Telegram",             "Linux": "telegram"},
    "discord":            {"Windows": "Discord",                 "Darwin": "Discord",              "Linux": "discord"},
    "slack":              {"Windows": "Slack",                   "Darwin": "Slack",                "Linux": "slack"},
    "zoom":               {"Windows": "Zoom",                    "Darwin": "zoom.us",              "Linux": "zoom"},
    "teams":              {"Windows": "msteams",                 "Darwin": "Microsoft Teams",      "Linux": "teams"},
    "microsoft teams":    {"Windows": "msteams",                 "Darwin": "Microsoft Teams",      "Linux": "teams"},
    "skype":              {"Windows": "skype",                   "Darwin": "Skype",                "Linux": "skype"},
    "signal":             {"Windows": "signal",                  "Darwin": "Signal",               "Linux": "signal"},

    # Media
    "spotify":            {"Windows": "Spotify",                 "Darwin": "Spotify",              "Linux": "spotify"},
    "vlc":                {"Windows": "vlc",                     "Darwin": "VLC",                  "Linux": "vlc"},
    "netflix":            {"Windows": "Netflix",                 "Darwin": "Netflix",              "Linux": "firefox"},
    "itunes":             {"Windows": "iTunes",                  "Darwin": "Music",                "Linux": "rhythmbox"},

    # Development
    "vscode":             {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "visual studio code": {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "vs code":            {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "terminal":           {"Windows": "wt",                      "Darwin": "Terminal",             "Linux": "gnome-terminal"},
    "cmd":                {"Windows": "cmd",                     "Darwin": "Terminal",             "Linux": "bash"},
    "powershell":         {"Windows": "powershell",              "Darwin": "Terminal",             "Linux": "bash"},
    "sublime":            {"Windows": "sublime_text",            "Darwin": "Sublime Text",         "Linux": "subl"},
    "notepad":            {"Windows": "notepad",                 "Darwin": "TextEdit",             "Linux": "gedit"},
    "notepad++":          {"Windows": "notepad++",               "Darwin": "TextEdit",             "Linux": "gedit"},

    # Productivity
    "word":               {"Windows": "winword",                 "Darwin": "Microsoft Word",       "Linux": "libreoffice --writer"},
    "excel":              {"Windows": "excel",                   "Darwin": "Microsoft Excel",      "Linux": "libreoffice --calc"},
    "powerpoint":         {"Windows": "powerpnt",                "Darwin": "Microsoft PowerPoint", "Linux": "libreoffice --impress"},
    "outlook":            {"Windows": "outlook",                 "Darwin": "Microsoft Outlook",    "Linux": "thunderbird"},

    # System
    "file explorer":      {"Windows": "explorer",                "Darwin": "Finder",               "Linux": "nautilus"},
    "explorer":           {"Windows": "explorer",                "Darwin": "Finder",               "Linux": "nautilus"},
    "finder":             {"Windows": "explorer",                "Darwin": "Finder",               "Linux": "nautilus"},
    "task manager":       {"Windows": "taskmgr",                 "Darwin": "Activity Monitor",     "Linux": "gnome-system-monitor"},
    "settings":           {"Windows": "ms-settings:",            "Darwin": "System Preferences",   "Linux": "gnome-control-center"},
    "calculator":         {"Windows": "calc",                    "Darwin": "Calculator",           "Linux": "gnome-calculator"},
    "paint":              {"Windows": "mspaint",                 "Darwin": "Preview",              "Linux": "gimp"},
    "snipping tool":      {"Windows": "SnippingTool",            "Darwin": "Screenshot",           "Linux": "gnome-screenshot"},
    "camera":             {"Windows": "microsoft.windows.camera:", "Darwin": "FaceTime",           "Linux": "cheese"},
    "clock":              {"Windows": "ms-clock:",               "Darwin": "Clock",                "Linux": "gnome-clocks"},
    "maps":               {"Windows": "bingmaps:",               "Darwin": "Maps",                 "Linux": "gnome-maps"},
    "store":              {"Windows": "ms-windows-store:",        "Darwin": "App Store",            "Linux": "gnome-software"},
}

# ── Process name mapping for closing apps ──
_PROCESS_NAMES: dict[str, list[str]] = {
    "chrome":     ["chrome.exe", "chrome", "Google Chrome"],
    "firefox":    ["firefox.exe", "firefox"],
    "edge":       ["msedge.exe", "Microsoft Edge"],
    "brave":      ["brave.exe", "brave"],
    "vscode":     ["Code.exe", "code"],
    "spotify":    ["Spotify.exe", "spotify"],
    "discord":    ["Discord.exe", "discord"],
    "whatsapp":   ["WhatsApp.exe", "WhatsApp"],
    "telegram":   ["Telegram.exe", "telegram"],
    "slack":      ["slack.exe", "slack"],
    "zoom":       ["Zoom.exe", "zoom"],
    "teams":      ["ms-teams.exe", "Teams.exe", "teams"],
    "notepad":    ["notepad.exe", "notepad"],
    "notepad++":  ["notepad++.exe"],
    "vlc":        ["vlc.exe", "vlc"],
    "word":       ["WINWORD.EXE", "Microsoft Word"],
    "excel":      ["EXCEL.EXE", "Microsoft Excel"],
    "powerpoint": ["POWERPNT.EXE", "Microsoft PowerPoint"],
    "outlook":    ["OUTLOOK.EXE", "Microsoft Outlook"],
    "explorer":   ["explorer.exe"],
    "calculator": ["Calculator.exe", "CalculatorApp.exe"],
    "task manager": ["Taskmgr.exe", "taskmgr.exe", "taskmgr"],
    "taskmgr":      ["Taskmgr.exe", "taskmgr.exe", "taskmgr"],
    "terminal":   ["WindowsTerminal.exe", "wt.exe"],
    "cmd":        ["cmd.exe"],
    "powershell": ["powershell.exe", "pwsh.exe"],
}


class AppController:
    """Cross-platform application launcher and closer."""

    def is_web_target(self, name: str) -> bool:
        """Return True if name is a known website or web target."""
        return get_web_target_url(name) is not None

    def open_app(self, app_name: str) -> str:
        """
        Open an application or web service by friendly name.

        Resolves web targets (e.g. YouTube, GitHub), aliases,
        tries multiple launch strategies, and returns a confirmation message.
        """
        app_key = app_name.lower().strip()

        # 1. Handle Web targets (YouTube, GitHub, Google, websites, URLs)
        web_url = get_web_target_url(app_key)
        if web_url:
            logger.info(f"Opening web target: '{app_name}' → '{web_url}'")
            try:
                webbrowser.open(web_url)
                return f"Opened {app_name} in browser"
            except Exception as e:
                logger.error(f"Failed to open web target '{app_name}': {e}")
                return f"Failed to open {app_name}: {e}"

        alias_entry = _APP_ALIASES.get(app_key)

        if alias_entry:
            target = alias_entry.get(_SYSTEM, app_key)
        else:
            target = app_name

        logger.info(f"Opening app: '{app_name}' → target='{target}' on {_SYSTEM}")

        try:
            if _SYSTEM == "Windows":
                return self._open_windows(target, app_name)
            elif _SYSTEM == "Darwin":
                return self._open_macos(target, app_name)
            else:
                return self._open_linux(target, app_name)
        except Exception as e:
            logger.error(f"Failed to open '{app_name}': {e}")
            return f"Failed to open {app_name}: {e}"

    def close_app(self, app_name: str) -> str:
        """
        Close an application by name.

        Uses psutil to find and terminate matching processes.
        """
        if not _HAS_PSUTIL:
            return "Cannot close apps: psutil not installed"

        app_key = app_name.lower().strip()
        process_names = _PROCESS_NAMES.get(app_key, [app_name])

        closed = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = proc.info.get("name", "")
                if not proc_name:
                    continue
                for target in process_names:
                    if target.lower() in proc_name.lower():
                        proc.terminate()
                        closed += 1
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if closed == 0:
            # Try matching by the raw name as fallback
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    proc_name = proc.info.get("name", "")
                    if proc_name and app_name.lower() in proc_name.lower():
                        proc.terminate()
                        closed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if closed == 0:
            return f"No running process found for '{app_name}'"

        logger.info(f"Closed {closed} process(es) for '{app_name}'")
        return f"Closed {app_name} ({closed} process{'es' if closed > 1 else ''} terminated)"

    def focus_app(self, app_name: str) -> str:
        """Focus an already-running application window (Windows only for now)."""
        if _SYSTEM != "Windows":
            return f"Focus is only supported on Windows currently"

        app_key = app_name.lower().strip()
        alias_entry = _APP_ALIASES.get(app_key)
        target = alias_entry.get(_SYSTEM, app_name) if alias_entry else app_name

        try:
            # Use PowerShell to bring window to front
            ps_cmd = (
                f'$p = Get-Process -Name "{target}" -ErrorAction SilentlyContinue | '
                f'Select-Object -First 1; '
                f'if ($p) {{ '
                f'  Add-Type -TypeDefinition \'using System; using System.Runtime.InteropServices; '
                f'  public class Win32 {{ [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd); }}\'; '
                f'  [Win32]::SetForegroundWindow($p.MainWindowHandle) '
                f'}} else {{ Write-Output "NOT_FOUND" }}'
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if _SYSTEM == "Windows" else 0,
            )
            if "NOT_FOUND" in result.stdout:
                return f"'{app_name}' is not running. Use 'open' to launch it."
            return f"Focused {app_name}"
        except Exception as e:
            return f"Could not focus {app_name}: {e}"

    def list_running_apps(self) -> list[dict]:
        """List user-visible running applications."""
        if not _HAS_PSUTIL:
            return [{"error": "psutil not installed"}]

        apps = {}
        system_procs = {
            "system", "idle", "svchost", "csrss", "wininit", "services",
            "lsass", "smss", "conhost", "dwm", "fontdrvhost", "sihost",
            "ctfmon", "taskhostw", "runtimebroker", "searchhost",
            "startmenuexperiencehost", "shellexperiencehost", "textinputhost",
            "applicationframehost", "systemsettings", "lockapp",
        }

        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                name = proc.info.get("name", "")
                if not name:
                    continue
                base_name = name.lower().replace(".exe", "")
                if base_name in system_procs:
                    continue
                if name not in apps:
                    apps[name] = {
                        "name": name,
                        "pid": proc.info["pid"],
                        "cpu_percent": round(proc.info.get("cpu_percent", 0) or 0, 1),
                        "memory_percent": round(proc.info.get("memory_percent", 0) or 0, 1),
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by memory usage descending
        sorted_apps = sorted(apps.values(), key=lambda a: a["memory_percent"], reverse=True)
        return sorted_apps[:30]

    # ── Platform-specific openers ──

    def _open_windows(self, target: str, display_name: str) -> str:
        """Open an app on Windows using multiple safe strategies."""
        # Sanitize target against shell injection
        forbidden = set("&|;><`$\r\n")
        if any(c in forbidden for c in target):
            return f"Blocked launching '{target}': invalid characters in application name."

        # Strategy 1: os.startfile (handles direct executables, ShellExecute aliases, and UWP URI schemes)
        try:
            os.startfile(target)
            return f"Opened {display_name}"
        except Exception:
            pass

        # Strategy 2: Direct executable via cmd /c start (safe, shell=False)
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", target],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return f"Opened {display_name}"
        except Exception:
            pass

        # Strategy 3: PowerShell Start-Process with safe parameters
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", f'Start-Process -FilePath "{target}"'],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return f"Opened {display_name}"
        except Exception:
            pass

        # Strategy 4: Search Start Menu via PowerShell
        try:
            safe_name = re.sub(r'[^a-zA-Z0-9 _-]', '', display_name)
            ps_cmd = (
                f'$app = Get-StartApps | Where-Object {{ $_.Name -like "*{safe_name}*" }} | '
                f'Select-Object -First 1; '
                f'if ($app) {{ Start-Process "shell:AppsFolder\\$($app.AppID)" }}'
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                return f"Opened {display_name}"
        except Exception:
            pass

        raise RuntimeError(f"All launch strategies failed for '{display_name}'")

    def _open_macos(self, target: str, display_name: str) -> str:
        """Open an app on macOS."""
        subprocess.Popen(["open", "-a", target])
        return f"Opened {display_name}"

    def _open_linux(self, target: str, display_name: str) -> str:
        """Open an app on Linux."""
        # Split for commands with arguments (e.g., "libreoffice --writer")
        parts = target.split()
        subprocess.Popen(parts, start_new_session=True)
        return f"Opened {display_name}"


# Singleton
app_controller = AppController()
