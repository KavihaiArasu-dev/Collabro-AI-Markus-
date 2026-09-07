"""
Markus AI — System Monitor (inspired by Jarvis system_monitor.py)

Enhanced system monitoring with:
- Battery status (percentage, charging, time remaining)
- Network info (IP, speed, connectivity)
- Top processes by CPU/RAM
- Disk partitions with usage per drive
- System uptime
- Temperature sensors (if available)
"""

from __future__ import annotations

import logging
import platform
import socket
import time
from datetime import datetime, timedelta
from typing import Optional, Any

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

logger = logging.getLogger(__name__)
_SYSTEM = platform.system()


class SystemMonitor:
    """Enhanced system monitoring with battery, network, and disk info."""

    def get_full_system_info(self) -> dict:
        """Get comprehensive system information."""
        info: dict[str, Any] = {
            "platform": _SYSTEM,
            "platform_version": platform.version(),
            "processor": platform.processor(),
            "machine": platform.machine(),
            "hostname": socket.gethostname(),
        }

        if _HAS_PSUTIL:
            # CPU
            info["cpu_count_physical"] = psutil.cpu_count(logical=False)
            info["cpu_count_logical"] = psutil.cpu_count(logical=True)
            info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
            info["cpu_freq_mhz"] = None
            try:
                freq = psutil.cpu_freq()
                if freq:
                    info["cpu_freq_mhz"] = round(freq.current, 0)
            except Exception:
                pass

            # Memory
            mem = psutil.virtual_memory()
            info["ram_total_gb"] = round(mem.total / (1024**3), 2)
            info["ram_used_gb"] = round(mem.used / (1024**3), 2)
            info["ram_available_gb"] = round(mem.available / (1024**3), 2)
            info["ram_percent"] = mem.percent
            info["memory_total_gb"] = info["ram_total_gb"]
            info["memory_used_gb"] = info["ram_used_gb"]

            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            info["boot_time"] = boot_time.strftime("%Y-%m-%d %H:%M:%S")
            info["uptime"] = str(timedelta(seconds=int(uptime.total_seconds())))

        # GPU
        try:
            import GPUtil  # type: ignore
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                info["gpu_name"] = gpu.name
                info["gpu_memory_total_mb"] = gpu.memoryTotal
                info["gpu_memory_used_mb"] = gpu.memoryUsed
                info["gpu_load_percent"] = round(gpu.load * 100, 1)
                info["gpu_temperature_c"] = gpu.temperature
        except ImportError:
            info["gpu_name"] = "N/A"

        return info

    def get_system_info(self) -> dict:
        """Get system telemetry info (alias for get_full_system_info)."""
        return self.get_full_system_info()

    def get_battery(self) -> dict:
        """Get battery status information."""
        if not _HAS_PSUTIL:
            return {"error": "psutil not installed"}

        battery = psutil.sensors_battery()
        if not battery:
            return {
                "has_battery": False,
                "summary": "No battery detected (desktop PC)",
            }

        time_left = ""
        if battery.secsleft > 0 and battery.secsleft != psutil.POWER_TIME_UNLIMITED:
            hours = battery.secsleft // 3600
            minutes = (battery.secsleft % 3600) // 60
            time_left = f"{hours}h {minutes}m"
        elif battery.power_plugged:
            time_left = "Charging"
        else:
            time_left = "Calculating..."

        status = "Charging" if battery.power_plugged else "On battery"

        return {
            "has_battery": True,
            "percent": battery.percent,
            "plugged_in": battery.power_plugged,
            "status": status,
            "time_remaining": time_left,
            "summary": f"Battery: {battery.percent}% — {status}" + (f" ({time_left})" if time_left else ""),
        }

    def get_network_info(self) -> dict:
        """Get network information."""
        info: dict[str, Any] = {
            "hostname": socket.gethostname(),
            "connected": False,
        }

        # Check internet connectivity
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            info["connected"] = True
        except OSError:
            info["connected"] = False

        # Get local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            info["local_ip"] = s.getsockname()[0]
            s.close()
        except Exception:
            info["local_ip"] = "127.0.0.1"

        if _HAS_PSUTIL:
            # Network I/O stats
            try:
                net_io = psutil.net_io_counters()
                info["bytes_sent_mb"] = round(net_io.bytes_sent / (1024**2), 2)
                info["bytes_recv_mb"] = round(net_io.bytes_recv / (1024**2), 2)
                info["packets_sent"] = net_io.packets_sent
                info["packets_recv"] = net_io.packets_recv
            except Exception:
                pass

            # Network interfaces
            try:
                addrs = psutil.net_if_addrs()
                interfaces = []
                for iface, addr_list in addrs.items():
                    for addr in addr_list:
                        if addr.family == socket.AF_INET:
                            interfaces.append({
                                "interface": iface,
                                "ip": addr.address,
                                "netmask": addr.netmask,
                            })
                info["interfaces"] = interfaces
            except Exception:
                pass

        status = "Connected" if info["connected"] else "Disconnected"
        info["summary"] = f"Network: {status} — IP: {info.get('local_ip', 'N/A')}"
        return info

    def get_disk_info(self) -> list[dict]:
        """Get disk partition information."""
        if not _HAS_PSUTIL:
            return [{"error": "psutil not installed"}]

        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent,
                })
            except (PermissionError, OSError):
                continue

        return disks

    def get_top_processes(self, limit: int = 10, sort_by: str = "cpu") -> list[dict]:
        """Get top processes sorted by CPU or memory usage."""
        if not _HAS_PSUTIL:
            return [{"error": "psutil not installed"}]

        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                info = proc.info
                if info.get("name"):
                    processes.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu_percent": round(info.get("cpu_percent", 0) or 0, 1),
                        "memory_percent": round(info.get("memory_percent", 0) or 0, 1),
                        "status": info.get("status", ""),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        sort_key = "cpu_percent" if sort_by == "cpu" else "memory_percent"
        processes.sort(key=lambda p: p.get(sort_key, 0), reverse=True)
        return processes[:limit]

    def get_uptime(self) -> str:
        """Get system uptime as a human-readable string."""
        if not _HAS_PSUTIL:
            return "Unknown (psutil not installed)"

        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        return f"System uptime: {', '.join(parts)}"

    def get_summary(self) -> str:
        """Get a quick human-readable system summary."""
        lines = ["**System Status:**\n"]

        if _HAS_PSUTIL:
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            lines.append(f"🖥️ CPU: {cpu}%")
            lines.append(f"💾 RAM: {mem.percent}% ({round(mem.used / (1024**3), 1)}/{round(mem.total / (1024**3), 1)} GB)")

            battery = psutil.sensors_battery()
            if battery:
                status = "⚡ Charging" if battery.power_plugged else "🔋 On battery"
                lines.append(f"🔋 Battery: {battery.percent}% — {status}")

            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            lines.append(f"⏱️ Uptime: {str(timedelta(seconds=int(uptime.total_seconds())))}")

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            lines.append(f"🌐 Network: Connected ({ip})")
        except OSError:
            lines.append("🌐 Network: Disconnected")

        return "\n".join(lines)


# Singleton
system_monitor = SystemMonitor()
