"""
Markus AI — System Settings Controller (inspired by Jarvis computer_settings.py)

Controls system settings via voice commands:
- Volume: mute/unmute, set level, increase/decrease
- Brightness: set level, increase/decrease
- Screenshot: full screen or active window
- Lock screen, shutdown, restart
- Wi-Fi: toggle, list networks

All dependencies are optional with graceful fallbacks.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

_SYSTEM = platform.system()

# ── Optional imports for volume control ──
_HAS_PYCAW = False
try:
    if _SYSTEM == "Windows":
        from comtypes import CLSCTX_ALL  # type: ignore
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore
        _HAS_PYCAW = True
except ImportError:
    pass

# ── Optional imports for brightness ──
_HAS_BRIGHTNESS = False
try:
    import screen_brightness_control as sbc  # type: ignore
    _HAS_BRIGHTNESS = True
except ImportError:
    pass

# ── Optional imports for screenshot ──
_HAS_PIL = False
try:
    from PIL import ImageGrab  # type: ignore
    _HAS_PIL = True
except ImportError:
    pass


class SystemSettings:
    """System settings controller for volume, brightness, screenshots, and power."""

    # ── Volume Control ──

    def set_volume(self, action: str, level: Optional[int] = None) -> str:
        """
        Control system volume.

        Args:
            action: "mute", "unmute", "up", "down", "set"
            level: 0-100 (used when action is "set")
        """
        action = action.lower().strip()

        if _SYSTEM == "Windows":
            return self._volume_windows(action, level)
        elif _SYSTEM == "Darwin":
            return self._volume_macos(action, level)
        else:
            return self._volume_linux(action, level)

    @staticmethod
    def _run_cmd(cmd: list[str], timeout: float = 5, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
        """Run a command suppressing console window popup on Windows."""
        if _SYSTEM == "Windows":
            return subprocess.run(
                cmd,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        return subprocess.run(cmd, timeout=timeout, capture_output=capture_output, text=True)

    def _volume_windows(self, action: str, level: Optional[int]) -> str:
        """Control volume on Windows using pycaw or nircmd fallback."""
        if _HAS_PYCAW:
            try:
                speakers = AudioUtilities.GetSpeakers()
                # Modern pycaw provides EndpointVolume directly; fallback to QueryInterface
                if hasattr(speakers, "EndpointVolume"):
                    volume = speakers.EndpointVolume
                else:
                    interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = interface.QueryInterface(IAudioEndpointVolume)

                if action == "mute":
                    volume.SetMute(1, None)
                    return "System volume muted"
                elif action == "unmute":
                    volume.SetMute(0, None)
                    return "System volume unmuted"
                elif action == "up":
                    current = volume.GetMasterVolumeLevelScalar()
                    new_level = min(1.0, current + 0.1)
                    volume.SetMasterVolumeLevelScalar(new_level, None)
                    return f"Volume increased to {int(new_level * 100)}%"
                elif action == "down":
                    current = volume.GetMasterVolumeLevelScalar()
                    new_level = max(0.0, current - 0.1)
                    volume.SetMasterVolumeLevelScalar(new_level, None)
                    return f"Volume decreased to {int(new_level * 100)}%"
                elif action == "set" and level is not None:
                    volume.SetMasterVolumeLevelScalar(max(0, min(100, level)) / 100.0, None)
                    return f"Volume set to {level}%"
                elif action == "get":
                    current = volume.GetMasterVolumeLevelScalar()
                    is_muted = volume.GetMute()
                    return f"Volume: {int(current * 100)}% {'(muted)' if is_muted else ''}"
                else:
                    return f"Unknown volume action: {action}"
            except Exception as e:
                logger.warning(f"pycaw volume control failed: {e}")

        # Fallback: PowerShell
        try:
            if action == "mute":
                self._run_cmd(
                    ["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"],
                    timeout=5,
                )
                return "System volume muted"
            elif action == "up":
                self._run_cmd(
                    ["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"],
                    timeout=5,
                )
                return "Volume increased"
            elif action == "down":
                self._run_cmd(
                    ["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"],
                    timeout=5,
                )
                return "Volume decreased"
            else:
                return f"Volume action '{action}' requires pycaw library. Install: pip install pycaw"
        except Exception as e:
            return f"Volume control failed: {e}"

    def _volume_macos(self, action: str, level: Optional[int]) -> str:
        """Control volume on macOS using osascript."""
        try:
            if action == "mute":
                subprocess.run(["osascript", "-e", "set volume with output muted"], timeout=5)
                return "System volume muted"
            elif action == "unmute":
                subprocess.run(["osascript", "-e", "set volume without output muted"], timeout=5)
                return "System volume unmuted"
            elif action == "set" and level is not None:
                vol = max(0, min(100, level)) * 7 // 100  # macOS uses 0-7
                subprocess.run(["osascript", "-e", f"set volume output volume {level}"], timeout=5)
                return f"Volume set to {level}%"
            elif action in ("up", "down"):
                result = subprocess.run(
                    ["osascript", "-e", "output volume of (get volume settings)"],
                    capture_output=True, text=True, timeout=5
                )
                current = int(result.stdout.strip()) if result.stdout.strip() else 50
                new_level = min(100, current + 10) if action == "up" else max(0, current - 10)
                subprocess.run(["osascript", "-e", f"set volume output volume {new_level}"], timeout=5)
                return f"Volume {'increased' if action == 'up' else 'decreased'} to {new_level}%"
            else:
                return f"Unknown volume action: {action}"
        except Exception as e:
            return f"Volume control failed: {e}"

    def _volume_linux(self, action: str, level: Optional[int]) -> str:
        """Control volume on Linux using amixer/pactl."""
        try:
            if action == "mute":
                subprocess.run(["amixer", "set", "Master", "mute"], timeout=5)
                return "System volume muted"
            elif action == "unmute":
                subprocess.run(["amixer", "set", "Master", "unmute"], timeout=5)
                return "System volume unmuted"
            elif action == "up":
                subprocess.run(["amixer", "set", "Master", "10%+"], timeout=5)
                return "Volume increased"
            elif action == "down":
                subprocess.run(["amixer", "set", "Master", "10%-"], timeout=5)
                return "Volume decreased"
            elif action == "set" and level is not None:
                subprocess.run(["amixer", "set", "Master", f"{level}%"], timeout=5)
                return f"Volume set to {level}%"
            else:
                return f"Unknown volume action: {action}"
        except Exception as e:
            return f"Volume control failed: {e}"

    # ── Brightness Control ──

    def set_brightness(self, action: str, level: Optional[int] = None) -> str:
        """
        Control screen brightness.

        Args:
            action: "up", "down", "set", "get"
            level: 0-100 (used when action is "set")
        """
        if not _HAS_BRIGHTNESS:
            return "Brightness control not available. Install: pip install screen-brightness-control"

        try:
            if action == "get":
                current = sbc.get_brightness()
                return f"Screen brightness: {current[0] if isinstance(current, list) else current}%"
            elif action == "set" and level is not None:
                sbc.set_brightness(max(0, min(100, level)))
                return f"Brightness set to {level}%"
            elif action == "up":
                current = sbc.get_brightness()
                curr_val = current[0] if isinstance(current, list) else current
                new_level = min(100, curr_val + 10)
                sbc.set_brightness(new_level)
                return f"Brightness increased to {new_level}%"
            elif action == "down":
                current = sbc.get_brightness()
                curr_val = current[0] if isinstance(current, list) else current
                new_level = max(0, curr_val - 10)
                sbc.set_brightness(new_level)
                return f"Brightness decreased to {new_level}%"
            else:
                return f"Unknown brightness action: {action}"
        except Exception as e:
            return f"Brightness control failed: {e}"

    # ── Screenshot ──

    def take_screenshot(self, save_path: Optional[str] = None) -> str:
        """
        Take a screenshot and save it.

        Args:
            save_path: Where to save. Defaults to Desktop/markus_screenshot_<timestamp>.png
        """
        import threading

        if not save_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = str(Path.home() / "Desktop" / f"markus_screenshot_{timestamp}.png")

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Strategy 1 & 2: Dedicated clean thread with desktop binding
        # On Windows, SetThreadDesktop requires a fresh thread without existing HWNDs or hooks.
        grab_result: dict[str, Any] = {"success": False, "error": None}

        def _thread_capture():
            if _SYSTEM == "Windows":
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
                    if hdesk:
                        user32.SetThreadDesktop(hdesk)
                except Exception as dt_err:
                    logger.debug(f"Desktop switch notice: {dt_err}")

            # Try Pillow ImageGrab
            if _HAS_PIL:
                try:
                    screenshot = ImageGrab.grab()
                    screenshot.save(save_path)
                    grab_result["success"] = True
                    return
                except Exception as pil_err:
                    logger.debug(f"Worker ImageGrab failed: {pil_err}")

            # Try mss
            try:
                import mss
                with mss.mss() as sct:
                    sct.shot(mon=-1, output=save_path)
                if Path(save_path).exists() and Path(save_path).stat().st_size > 0:
                    grab_result["success"] = True
                    return
            except Exception as mss_err:
                logger.debug(f"Worker mss failed: {mss_err}")

        capture_thread = threading.Thread(target=_thread_capture, daemon=True)
        capture_thread.start()
        capture_thread.join(timeout=8.0)

        if grab_result["success"] and Path(save_path).exists() and Path(save_path).stat().st_size > 0:
            logger.info(f"Screenshot saved to {save_path}")
            return f"Screenshot saved to {save_path}"

        # Strategy 3: Native OS fallbacks
        if _SYSTEM == "Windows":
            try:
                subprocess.Popen(
                    ["powershell", "-WindowStyle", "Hidden", "-Command", "Start-Process ms-screenclip:"],
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return "Opened Windows Snipping Tool for screenshot"
            except Exception:
                try:
                    subprocess.Popen(
                        ["SnippingTool", "/clip"],
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    return "Opened Snipping Tool for screenshot"
                except Exception as snip_err:
                    return f"Screenshot failed: {snip_err}"
        elif _SYSTEM == "Darwin":
            try:
                subprocess.run(["screencapture", save_path], timeout=10)
                if Path(save_path).exists():
                    return f"Screenshot saved to {save_path}"
            except Exception as mac_err:
                return f"Screenshot failed: {mac_err}"

        return "Screenshot failed: no working screen capture backend available"

    # ── Power Management ──

    def lock_screen(self) -> str:
        """Lock the screen."""
        try:
            if _SYSTEM == "Windows":
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], timeout=5)
            elif _SYSTEM == "Darwin":
                subprocess.run(["pmset", "displaysleepnow"], timeout=5)
            else:
                subprocess.run(["loginctl", "lock-session"], timeout=5)
            return "Screen locked"
        except Exception as e:
            return f"Failed to lock screen: {e}"

    def shutdown(self, delay_seconds: int = 0) -> str:
        """Initiate system shutdown (requires confirmation in tool router)."""
        try:
            if _SYSTEM == "Windows":
                subprocess.run(["shutdown", "/s", "/t", str(delay_seconds)], timeout=5)
            elif _SYSTEM == "Darwin":
                subprocess.run(["sudo", "shutdown", "-h", f"+{delay_seconds // 60}"], timeout=5)
            else:
                subprocess.run(["sudo", "shutdown", "-h", f"+{delay_seconds // 60}"], timeout=5)
            return f"System shutdown initiated (delay: {delay_seconds}s)"
        except Exception as e:
            return f"Shutdown failed: {e}"

    def restart(self, delay_seconds: int = 0) -> str:
        """Initiate system restart (requires confirmation in tool router)."""
        try:
            if _SYSTEM == "Windows":
                subprocess.run(["shutdown", "/r", "/t", str(delay_seconds)], timeout=5)
            elif _SYSTEM == "Darwin":
                subprocess.run(["sudo", "shutdown", "-r", f"+{delay_seconds // 60}"], timeout=5)
            else:
                subprocess.run(["sudo", "shutdown", "-r", f"+{delay_seconds // 60}"], timeout=5)
            return f"System restart initiated (delay: {delay_seconds}s)"
        except Exception as e:
            return f"Restart failed: {e}"

    def cancel_shutdown(self) -> str:
        """Cancel a pending shutdown/restart."""
        try:
            if _SYSTEM == "Windows":
                subprocess.run(["shutdown", "/a"], timeout=5)
            else:
                subprocess.run(["sudo", "shutdown", "-c"], timeout=5)
            return "Shutdown/restart cancelled"
        except Exception as e:
            return f"Failed to cancel shutdown: {e}"

    # ── Wi-Fi ──

    def wifi_list(self) -> str:
        """List available Wi-Fi networks."""
        try:
            if _SYSTEM == "Windows":
                result = self._run_cmd(
                    ["netsh", "wlan", "show", "networks"],
                    capture_output=True, timeout=10,
                )
                return result.stdout or "No Wi-Fi networks found"
            elif _SYSTEM == "Darwin":
                result = subprocess.run(
                    ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"],
                    capture_output=True, text=True, timeout=10
                )
                return result.stdout or "No Wi-Fi networks found"
            else:
                result = subprocess.run(
                    ["nmcli", "device", "wifi", "list"],
                    capture_output=True, text=True, timeout=10
                )
                return result.stdout or "No Wi-Fi networks found"
        except Exception as e:
            return f"Wi-Fi listing failed: {e}"


# Singleton
system_settings = SystemSettings()
