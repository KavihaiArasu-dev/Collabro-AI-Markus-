"""
Markus AI — Tool Registry & Router (§11a)

Deterministic tools for deterministic work:
- Open app → subprocess
- Read file → filesystem API
- Git status → Git CLI
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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import psutil

from config.constants import RiskLevel, PermissionDecision
from security.permissions import permission_manager

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definition of a tool with its metadata."""
    name: str
    description: str
    risk_level: RiskLevel
    handler: Optional[Callable] = None
    arguments: dict = field(default_factory=dict)
    timeout: int = 30
    requires_confirmation: bool = False


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
        ))

        # ── System Tools ──
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
            name="open_application",
            description="Open an application",
            risk_level=RiskLevel.LOW,
            handler=self._open_application,
            arguments={"app_name": "string"},
        ))
        self.register(ToolDefinition(
            name="close_application",
            description="Terminate a process by name",
            risk_level=RiskLevel.HIGH,
            handler=self._close_application,
            arguments={"process_name": "string"},
            requires_confirmation=True,
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

        # ── Browser Tools ──
        self.register(ToolDefinition(
            name="browser_open",
            description="Open a URL in the default web browser",
            risk_level=RiskLevel.LOW,
            handler=self._browser_open,
            arguments={"url": "string"},
        ))
        self.register(ToolDefinition(
            name="browser_search",
            description="Search the web using default search engine",
            risk_level=RiskLevel.LOW,
            handler=self._browser_search,
            arguments={"query": "string"},
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

    def register(self, tool: ToolDefinition):
        """Register a tool."""
        self._tools[tool.name] = tool

    async def execute(self, tool_name: str, arguments: dict, requested_by: str = "") -> dict:
        """
        Execute a tool after permission check.

        Returns:
            {"success": bool, "result": Any, "error": str | None}
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return {"success": False, "result": None, "error": f"Unknown tool: {tool_name}"}

        # Permission check
        perm = permission_manager.check_permission(
            action=tool_name,
            tool_name=tool_name,
            arguments=arguments,
            risk_level=tool.risk_level,
            requested_by=requested_by,
            description=tool.description,
        )

        if perm.decision == PermissionDecision.BLOCK:
            return {"success": False, "result": None, "error": "Permission denied"}

        if perm.decision == PermissionDecision.ASK:
            return {
                "success": False,
                "result": None,
                "error": "Waiting for user confirmation",
                "permission_request_id": perm.id,
                "requires_confirmation": True,
            }

        # Execute the tool
        try:
            if tool.handler:
                result = tool.handler(**arguments)
                return {"success": True, "result": result, "error": None}
            else:
                return {"success": False, "result": None, "error": "No handler registered"}
        except Exception as e:
            logger.error(f"Tool execution failed [{tool_name}]: {e}")
            return {"success": False, "result": None, "error": str(e)}

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
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": cpu_percent,
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_percent": mem.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_percent": round(disk.used / disk.total * 100, 1),
        }

        # Try to get GPU info
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                info["gpu_name"] = gpu.name
                info["gpu_memory_total_mb"] = gpu.memoryTotal
                info["gpu_memory_used_mb"] = gpu.memoryUsed
                info["gpu_load_percent"] = round(gpu.load * 100, 1)
        except ImportError:
            info["gpu_name"] = "N/A (GPUtil not installed)"

        return info

    def _open_application(self, app_name: str) -> str:
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(app_name)
            elif system == "Darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:
                subprocess.Popen([app_name])
            return f"Opened: {app_name}"
        except Exception as e:
            raise RuntimeError(f"Failed to open {app_name}: {e}")

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

    def _get_processes(self, limit: int = 20) -> list[dict]:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        processes.sort(key=lambda p: p.get('cpu_percent') or 0, reverse=True)
        return processes[:limit]

    def _close_application(self, process_name: str) -> str:
        closed = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                    proc.terminate()
                    closed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if closed == 0:
            return f"No process found matching '{process_name}'"
        return f"Terminated {closed} process(es) matching '{process_name}'"

    def _run_dev_command(self, command: str, cwd: str = ".") -> str:
        result = subprocess.run(
            command, cwd=cwd, shell=True, capture_output=True, text=True, timeout=60,
        )
        out = result.stdout
        if result.stderr:
            out += f"\nSTDERR: {result.stderr}"
        return out or "(Command finished with no output)"

    def _browser_open(self, url: str) -> str:
        import webbrowser
        webbrowser.open(url)
        return f"Opened {url} in web browser"

    def _browser_search(self, query: str) -> str:
        import urllib.parse
        import webbrowser
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(url)
        return f"Searching web for '{query}'"

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
            ["git", "log", f"-n {max_count}", "--oneline"], cwd=repo_path, capture_output=True, text=True, timeout=10,
        )
        return result.stdout or result.stderr


# Singleton
tool_router = ToolRouter()
