"""
Markus AI — Tool Registry & Router (§11a)

Deterministic tools for deterministic work:
- Open/Close/Focus apps → AppController
- Web search → WebSearchEngine
- YouTube search/play → YouTubeController
- Volume/Brightness/Screenshot → SystemSettings
- Battery/Network/Uptime → SystemMonitor
- File operations → filesystem API
- Git tools → Git CLI
- System metrics → psutil

Every tool carries: name, description, arguments, permissions, risk_level, timeout, rollback.
Chain: LLM → Planner → Permission Manager → Tool Router → OS
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import psutil

from config.constants import RiskLevel, PermissionDecision
from security.permissions import permission_manager
from core.verifier import verifier, VerificationResult
from tools.contracts import PreCondition, PostCondition, ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definition of a tool with its metadata, pre-conditions, and post-conditions."""
    name: str
    description: str
    risk_level: RiskLevel
    handler: Optional[Callable] = None
    arguments: dict = field(default_factory=dict)
    timeout: int = 30
    requires_confirmation: bool = False
    pre_conditions: list[PreCondition] = field(default_factory=list)
    post_conditions: list[PostCondition] = field(default_factory=list)


class ToolRouter:
    """
    Executes tools after permission checks.

    Every tool execution flows through:
    1. Look up tool definition
    2. Check permissions via Permission Manager
    3. If allowed, execute via deterministic handler
    4. Return result
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._register_builtin_tools()
        self._register_jarvis_tools()
        logger.info(f"Tool Router initialized with {len(self._tools)} tools")

    def _register_builtin_tools(self):
        """Register all built-in tools."""
        # ── File Tools ──
        self.register(ToolDefinition(
            name="read_file",
            description="Read the contents of a file",
            risk_level=RiskLevel.LOW,
            handler=self._read_file,
            arguments={"path": "string"},
        ))
        self.register(ToolDefinition(
            name="write_file",
            description="Write content to a file",
            risk_level=RiskLevel.MEDIUM,
            handler=self._write_file,
            arguments={"path": "string", "content": "string"},
            post_conditions=[PostCondition(assertion_type="file_exists", target_param="path", timeout=1.5)],
        ))
        self.register(ToolDefinition(
            name="list_directory",
            description="List files and folders in a directory",
            risk_level=RiskLevel.LOW,
            handler=self._list_directory,
            arguments={"path": "string"},
        ))
        self.register(ToolDefinition(
            name="delete_file",
            description="Delete a file",
            risk_level=RiskLevel.HIGH,
            handler=self._delete_file,
            arguments={"path": "string"},
            requires_confirmation=True,
            pre_conditions=[
                PreCondition(
                    name="file_exists",
                    check_fn=lambda **kw: Path(kw.get("path", "")).exists(),
                    failure_message="Target file does not exist",
                )
            ],
            post_conditions=[PostCondition(assertion_type="file_deleted", target_param="path", timeout=1.5)],
        ))

        # ── Extended File Tools ──
        self.register(ToolDefinition(
            name="search_files",
            description="Search files by name pattern or content keyword",
            risk_level=RiskLevel.LOW,
            handler=self._search_files,
            arguments={"directory": "string", "query": "string"},
        ))
        self.register(ToolDefinition(
            name="move_file",
            description="Move or rename a file or directory",
            risk_level=RiskLevel.MEDIUM,
            handler=self._move_file,
            arguments={"src": "string", "dst": "string"},
            pre_conditions=[
                PreCondition(
                    name="src_exists",
                    check_fn=lambda **kw: Path(kw.get("src", "")).exists(),
                    failure_message="Source file does not exist",
                )
            ],
            post_conditions=[PostCondition(assertion_type="file_moved", target_param="src", timeout=1.5)],
        ))

        # ── System Tools (legacy) ──
        self.register(ToolDefinition(
            name="system_info",
            description="Get system information (CPU, RAM, GPU, disk)",
            risk_level=RiskLevel.LOW,
            handler=self._system_info,
        ))
        self.register(ToolDefinition(
            name="get_processes",
            description="Get list of running system processes",
            risk_level=RiskLevel.LOW,
            handler=self._get_processes,
            arguments={"limit": "integer"},
        ))
        self.register(ToolDefinition(
            name="execute_command",
            description="Execute a shell command",
            risk_level=RiskLevel.HIGH,
            handler=self._execute_command,
            arguments={"command": "string"},
            requires_confirmation=True,
        ))
        self.register(ToolDefinition(
            name="run_dev_command",
            description="Run developer build/test command with output capture",
            risk_level=RiskLevel.MEDIUM,
            handler=self._run_dev_command,
            arguments={"command": "string", "cwd": "string"},
        ))

        # ── Git Tools ──
        self.register(ToolDefinition(
            name="git_status",
            description="Get git repository status",
            risk_level=RiskLevel.LOW,
            handler=self._git_status,
            arguments={"repo_path": "string"},
        ))
        self.register(ToolDefinition(
            name="git_diff",
            description="Get git repository diff",
            risk_level=RiskLevel.LOW,
            handler=self._git_diff,
            arguments={"repo_path": "string"},
        ))
        self.register(ToolDefinition(
            name="git_log",
            description="Get recent git commit log",
            risk_level=RiskLevel.LOW,
            handler=self._git_log,
            arguments={"repo_path": "string", "max_count": "integer"},
        ))

    def _register_jarvis_tools(self):
        """Register Jarvis-style desktop automation tools."""

        # ── App Control Tools ──
        self.register(ToolDefinition(
            name="open_app",
            description="Open an application by name (e.g., chrome, vscode, spotify, discord, whatsapp)",
            risk_level=RiskLevel.LOW,
            handler=self._open_app,
            arguments={"app_name": "string"},
            post_conditions=[PostCondition(assertion_type="process_running", target_param="app_name", timeout=2.5)],
        ))
        self.register(ToolDefinition(
            name="open_application",
            description="Open an application (alias for open_app)",
            risk_level=RiskLevel.LOW,
            handler=self._open_app,
            arguments={"app_name": "string"},
            post_conditions=[PostCondition(assertion_type="process_running", target_param="app_name", timeout=2.5)],
        ))
        self.register(ToolDefinition(
            name="close_app",
            description="Close/terminate an application by name",
            risk_level=RiskLevel.MEDIUM,
            handler=self._close_app,
            arguments={"app_name": "string"},
            post_conditions=[PostCondition(assertion_type="process_terminated", target_param="app_name", timeout=2.5)],
        ))
        self.register(ToolDefinition(
            name="close_application",
            description="Close/terminate an application (alias for close_app)",
            risk_level=RiskLevel.MEDIUM,
            handler=self._close_app,
            arguments={"app_name": "string"},
            post_conditions=[PostCondition(assertion_type="process_terminated", target_param="app_name", timeout=2.5)],
        ))
        self.register(ToolDefinition(
            name="focus_app",
            description="Focus/switch to an already-running application window",
            risk_level=RiskLevel.LOW,
            handler=self._focus_app,
            arguments={"app_name": "string"},
            post_conditions=[PostCondition(assertion_type="window_focused", target_param="app_name", timeout=2.0)],
        ))
        self.register(ToolDefinition(
            name="list_running_apps",
            description="List all currently running user applications",
            risk_level=RiskLevel.LOW,
            handler=self._list_running_apps,
        ))

        # ── Web Search Tools ──
        self.register(ToolDefinition(
            name="web_search",
            description="Search the web using DuckDuckGo and return results",
            risk_level=RiskLevel.LOW,
            handler=self._web_search,
            arguments={"query": "string"},
        ))
        self.register(ToolDefinition(
            name="web_search_news",
            description="Search for latest news articles",
            risk_level=RiskLevel.LOW,
            handler=self._web_search_news,
            arguments={"query": "string"},
        ))
        self.register(ToolDefinition(
            name="browser_open",
            description="Open a URL in the default web browser",
            risk_level=RiskLevel.LOW,
            handler=self._browser_open,
            arguments={"url": "string"},
        ))
        self.register(ToolDefinition(
            name="browser_search",
            description="Search the web using default search engine in browser",
            risk_level=RiskLevel.LOW,
            handler=self._browser_search,
            arguments={"query": "string"},
        ))

        # ── YouTube Tools ──
        self.register(ToolDefinition(
            name="youtube_search",
            description="Search for YouTube videos",
            risk_level=RiskLevel.LOW,
            handler=self._youtube_search,
            arguments={"query": "string"},
        ))
        self.register(ToolDefinition(
            name="youtube_play",
            description="Search and play a YouTube video or song",
            risk_level=RiskLevel.LOW,
            handler=self._youtube_play,
            arguments={"query": "string"},
        ))

        # ── System Settings Tools ──
        self.register(ToolDefinition(
            name="set_volume",
            description="Control system volume (mute/unmute/up/down/set)",
            risk_level=RiskLevel.LOW,
            handler=self._set_volume,
            arguments={"action": "string", "level": "integer"},
            post_conditions=[PostCondition(assertion_type="audio_volume", target_param="action", timeout=1.0)],
        ))
        self.register(ToolDefinition(
            name="set_brightness",
            description="Control screen brightness (up/down/set/get)",
            risk_level=RiskLevel.LOW,
            handler=self._set_brightness,
            arguments={"action": "string", "level": "integer"},
        ))
        self.register(ToolDefinition(
            name="take_screenshot",
            description="Take a screenshot and save it to Desktop",
            risk_level=RiskLevel.LOW,
            handler=self._take_screenshot,
            arguments={"save_path": "string"},
        ))
        self.register(ToolDefinition(
            name="lock_screen",
            description="Lock the screen",
            risk_level=RiskLevel.MEDIUM,
            handler=self._lock_screen,
        ))
        self.register(ToolDefinition(
            name="wifi_list",
            description="List available Wi-Fi networks",
            risk_level=RiskLevel.LOW,
            handler=self._wifi_list,
        ))

        # ── Enhanced System Monitor Tools ──
        self.register(ToolDefinition(
            name="get_battery",
            description="Get battery status (percentage, charging, time remaining)",
            risk_level=RiskLevel.LOW,
            handler=self._get_battery,
        ))
        self.register(ToolDefinition(
            name="get_network_info",
            description="Get network information (IP, connectivity, interfaces)",
            risk_level=RiskLevel.LOW,
            handler=self._get_network_info,
        ))
        self.register(ToolDefinition(
            name="get_disk_info",
            description="Get disk partition and usage information",
            risk_level=RiskLevel.LOW,
            handler=self._get_disk_info,
        ))
        self.register(ToolDefinition(
            name="get_uptime",
            description="Get system uptime",
            risk_level=RiskLevel.LOW,
            handler=self._get_uptime,
        ))
        self.register(ToolDefinition(
            name="get_system_summary",
            description="Get a quick system status summary (CPU, RAM, battery, network)",
            risk_level=RiskLevel.LOW,
            handler=self._get_system_summary,
        ))

        # ── Power Management (require confirmation) ──
        self.register(ToolDefinition(
            name="system_shutdown",
            description="Shutdown the computer",
            risk_level=RiskLevel.HIGH,
            handler=self._system_shutdown,
            requires_confirmation=True,
        ))
        self.register(ToolDefinition(
            name="system_restart",
            description="Restart the computer",
            risk_level=RiskLevel.HIGH,
            handler=self._system_restart,
            requires_confirmation=True,
        ))

    def register(self, tool: ToolDefinition):
        """Register a tool."""
        self._tools[tool.name] = tool

    def execute_sync(self, tool_name: str, arguments: dict, requested_by: str = "") -> dict:
        """
        Execute a tool synchronously with permission checks, pre-conditions, and post-condition verification.

        Returns:
            {"success": bool, "verified": bool, "result": Any, "verification": dict | None, "error": str | None, "execution_time_ms": float}
        """
        start_time = time.perf_counter()
        tool = self._tools.get(tool_name)
        if not tool:
            return {
                "success": False,
                "verified": False,
                "result": None,
                "verification": None,
                "error": f"Unknown tool: {tool_name}",
                "execution_time_ms": (time.perf_counter() - start_time) * 1000,
            }

        # 1. Pre-condition checks (fail fast before prompting user if prerequisites are not met)
        for pre in tool.pre_conditions:
            try:
                if not pre.check_fn(**arguments):
                    return {
                        "success": False,
                        "verified": False,
                        "result": None,
                        "verification": None,
                        "error": f"Pre-condition failed [{pre.name}]: {pre.failure_message}",
                        "execution_time_ms": (time.perf_counter() - start_time) * 1000,
                    }
            except Exception as e:
                return {
                    "success": False,
                    "verified": False,
                    "result": None,
                    "verification": None,
                    "error": f"Pre-condition error [{pre.name}]: {e}",
                    "execution_time_ms": (time.perf_counter() - start_time) * 1000,
                }

        # 2. Permission check
        perm = permission_manager.check_permission(
            action=tool_name,
            tool_name=tool_name,
            arguments=arguments,
            risk_level=tool.risk_level,
            requested_by=requested_by,
            description=tool.description,
        )

        if perm.decision == PermissionDecision.BLOCK:
            return {
                "success": False,
                "verified": False,
                "result": None,
                "verification": None,
                "error": "Permission denied",
                "execution_time_ms": (time.perf_counter() - start_time) * 1000,
            }

        if perm.decision == PermissionDecision.ASK:
            return {
                "success": False,
                "verified": False,
                "result": None,
                "verification": None,
                "error": "Waiting for user confirmation",
                "permission_request_id": perm.id,
                "requires_confirmation": True,
                "execution_time_ms": (time.perf_counter() - start_time) * 1000,
            }

        # 3. Handler execution
        try:
            if not tool.handler:
                return {
                    "success": False,
                    "verified": False,
                    "result": None,
                    "verification": None,
                    "error": "No handler registered",
                    "execution_time_ms": (time.perf_counter() - start_time) * 1000,
                }
            result = tool.handler(**arguments)
        except Exception as e:
            logger.error(f"Tool execution failed [{tool_name}]: {e}")
            return {
                "success": False,
                "verified": False,
                "result": None,
                "verification": None,
                "error": str(e),
                "execution_time_ms": (time.perf_counter() - start_time) * 1000,
            }

        # 4. Post-condition verification via Verifier
        verification_dict = None
        is_verified = True
        if tool.post_conditions:
            for post in tool.post_conditions:
                target_val = arguments.get(post.target_param)
                extra = {}
                if post.assertion_type == "file_moved":
                    extra["dst"] = arguments.get("dst")
                ver_res = verifier.verify_assertion(
                    post.assertion_type,
                    target_val,
                    timeout=post.timeout,
                    **extra,
                )
                verification_dict = ver_res.to_dict()
                if not ver_res.verified:
                    is_verified = False
                    return {
                        "success": False,
                        "verified": False,
                        "result": result,
                        "verification": verification_dict,
                        "error": f"Verification failed: {ver_res.details}",
                        "execution_time_ms": (time.perf_counter() - start_time) * 1000,
                    }

        return {
            "success": True,
            "verified": is_verified,
            "result": result,
            "verification": verification_dict,
            "error": None,
            "execution_time_ms": (time.perf_counter() - start_time) * 1000,
        }

    async def execute(self, tool_name: str, arguments: dict, requested_by: str = "") -> dict:
        """
        Asynchronous wrapper around execute_sync.
        """
        return self.execute_sync(tool_name, arguments, requested_by)

    def list_tools(self) -> list[dict]:
        """List all available tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level.value,
                "arguments": t.arguments,
                "requires_confirmation": t.requires_confirmation,
            }
            for t in self._tools.values()
        ]

    # ── Built-in Tool Handlers ──

    def _read_file(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return p.read_text(encoding="utf-8", errors="ignore")

    def _write_file(self, path: str, content: str) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {path}"

    def _list_directory(self, path: str) -> list[dict]:
        p = Path(path)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        return [
            {"name": item.name, "is_dir": item.is_dir(), "size": item.stat().st_size if item.is_file() else 0}
            for item in sorted(p.iterdir())
        ]

    def _delete_file(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if p.is_dir():
            shutil.rmtree(str(p))
        else:
            p.unlink()
        return f"Deleted: {path}"

    def _system_info(self) -> dict:
        from actions.system_monitor import system_monitor
        return system_monitor.get_full_system_info()

    def _get_processes(self, limit: int = 20) -> list[dict]:
        from actions.system_monitor import system_monitor
        return system_monitor.get_top_processes(limit=limit)

    def _execute_command(self, command: str) -> str:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        return output or "(no output)"

    def _search_files(self, directory: str, query: str) -> list[str]:
        p = Path(directory)
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")
        results = []
        for item in p.rglob("*"):
            if query.lower() in item.name.lower():
                results.append(str(item))
            elif item.is_file():
                try:
                    if query.lower() in item.read_text(encoding="utf-8", errors="ignore").lower():
                        results.append(str(item))
                except Exception:
                    pass
            if len(results) >= 50:
                break
        return results

    def _move_file(self, src: str, dst: str) -> str:
        src_path = Path(src)
        dst_path = Path(dst)
        if not src_path.exists():
            raise FileNotFoundError(f"Source not found: {src}")
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        return f"Moved {src} to {dst}"

    def _run_dev_command(self, command: str, cwd: str = ".") -> str:
        result = subprocess.run(
            command, cwd=cwd, shell=True, capture_output=True, text=True, timeout=60,
        )
        out = result.stdout
        if result.stderr:
            out += f"\nSTDERR: {result.stderr}"
        return out or "(Command finished with no output)"

    def _git_status(self, repo_path: str) -> str:
        result = subprocess.run(
            ["git", "status"], cwd=repo_path, capture_output=True, text=True, timeout=10,
        )
        return result.stdout or result.stderr

    def _git_diff(self, repo_path: str) -> str:
        result = subprocess.run(
            ["git", "diff"], cwd=repo_path, capture_output=True, text=True, timeout=10,
        )
        return result.stdout or "(No uncommitted changes)"

    def _git_log(self, repo_path: str, max_count: int = 5) -> str:
        result = subprocess.run(
            ["git", "log", f"-n{max_count}", "--oneline"], cwd=repo_path, capture_output=True, text=True, timeout=10,
        )
        return result.stdout or result.stderr

    # ── Jarvis-style Tool Handlers ──
    # These delegate to the action modules for clean separation.

    def _open_app(self, app_name: str) -> str:
        from actions.app_controller import app_controller
        return app_controller.open_app(app_name)

    def _close_app(self, app_name: str) -> str:
        from actions.app_controller import app_controller
        return app_controller.close_app(app_name)

    def _focus_app(self, app_name: str) -> str:
        from actions.app_controller import app_controller
        return app_controller.focus_app(app_name)

    def _list_running_apps(self) -> list[dict]:
        from actions.app_controller import app_controller
        return app_controller.list_running_apps()

    def _web_search(self, query: str) -> dict:
        from actions.web_search import web_search_engine
        return web_search_engine.search(query)

    def _web_search_news(self, query: str) -> dict:
        from actions.web_search import web_search_engine
        return web_search_engine.search_news(query)

    def _browser_open(self, url: str) -> str:
        from actions.web_search import web_search_engine
        return web_search_engine.open_url(url)

    def _browser_search(self, query: str) -> str:
        from actions.web_search import web_search_engine
        return web_search_engine.open_in_browser(query)

    def _youtube_search(self, query: str) -> dict:
        from actions.youtube_controller import youtube_controller
        return youtube_controller.search(query)

    def _youtube_play(self, query: str) -> str:
        from actions.youtube_controller import youtube_controller
        return youtube_controller.play(query)

    def _set_volume(self, action: str, level: Optional[int] = None) -> str:
        from actions.system_settings import system_settings
        return system_settings.set_volume(action, level)

    def _set_brightness(self, action: str, level: Optional[int] = None) -> str:
        from actions.system_settings import system_settings
        return system_settings.set_brightness(action, level)

    def _take_screenshot(self, save_path: Optional[str] = None) -> str:
        from actions.system_settings import system_settings
        return system_settings.take_screenshot(save_path)

    def _lock_screen(self) -> str:
        from actions.system_settings import system_settings
        return system_settings.lock_screen()

    def _wifi_list(self) -> str:
        from actions.system_settings import system_settings
        return system_settings.wifi_list()

    def _get_battery(self) -> dict:
        from actions.system_monitor import system_monitor
        return system_monitor.get_battery()

    def _get_network_info(self) -> dict:
        from actions.system_monitor import system_monitor
        return system_monitor.get_network_info()

    def _get_disk_info(self) -> list[dict]:
        from actions.system_monitor import system_monitor
        return system_monitor.get_disk_info()

    def _get_uptime(self) -> str:
        from actions.system_monitor import system_monitor
        return system_monitor.get_uptime()

    def _get_system_summary(self) -> str:
        from actions.system_monitor import system_monitor
        return system_monitor.get_summary()

    def _system_shutdown(self) -> str:
        from actions.system_settings import system_settings
        return system_settings.shutdown()

    def _system_restart(self) -> str:
        from actions.system_settings import system_settings
        return system_settings.restart()


# Singleton
tool_router = ToolRouter()
