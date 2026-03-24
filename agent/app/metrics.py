import os
import time
from datetime import timedelta

import psutil

PROCFS = os.getenv("PROCFS_PATH", "/proc")
SYSFS = os.getenv("SYSFS_PATH", "/sys")

psutil.PROCFS_PATH = PROCFS


def get_uptime() -> tuple[int, str]:
    boot = psutil.boot_time()
    seconds = int(time.time() - boot)
    d = timedelta(seconds=seconds)
    h, rem = divmod(d.seconds, 3600)
    m, _ = divmod(rem, 60)
    return seconds, f"{d.days}d {h}h {m}m"


def get_cpu_temp_avg() -> float | None:
    thermal_root = os.path.join(SYSFS, "class", "thermal")
    values = []
    try:
        for zone in os.listdir(thermal_root):
            temp_file = os.path.join(thermal_root, zone, "temp")
            try:
                with open(temp_file) as f:
                    values.append(int(f.read().strip()) / 1000)
            except (OSError, ValueError):
                continue
    except OSError:
        pass

    if not values:
        try:
            temps = psutil.sensors_temperatures()
            for entries in temps.values():
                for e in entries:
                    if e.current is not None:
                        values.append(e.current)
        except Exception:
            pass

    return round(sum(values) / len(values), 1) if values else None


def collect() -> dict:
    uptime_sec, uptime_human = get_uptime()
    load = psutil.getloadavg()
    mem = psutil.virtual_memory()

    return {
        "node_name": os.getenv("NODE_NAME", "unknown"),
        "uptime_seconds": uptime_sec,
        "uptime_human": uptime_human,
        "cpu": {
            "percent": psutil.cpu_percent(interval=0.1),
            "load_1m": round(load[0], 2),
            "load_5m": round(load[1], 2),
            "load_15m": round(load[2], 2),
        },
        "ram": {
            "used_mb": int(mem.used / 1024 / 1024),
            "total_mb": int(mem.total / 1024 / 1024),
            "percent": mem.percent,
        },
        "temperature": {
            "cpu_avg": get_cpu_temp_avg(),
        },
    }
