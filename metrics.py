import os
import httpx
from app.k8s_client import get_clients


# Optional: map node names to server-stats URLs for temperature data
# e.g. NODE_STATS_URLS=node-1=http://node-1:8000,node-2=http://node-2:8000
def _parse_stats_urls() -> dict[str, str]:
    raw = os.getenv("NODE_STATS_URLS", "")
    result = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" in part:
            name, url = part.split("=", 1)
            result[name.strip()] = url.strip()
    return result


NODE_STATS_URLS = _parse_stats_urls()


def _parse_cpu(s: str) -> float:
    """Parse k8s CPU string → cores (float).
    Examples: '4' → 4.0, '500m' → 0.5, '1200000000n' → 1.2
    """
    if s.endswith("n"):
        return int(s[:-1]) / 1_000_000_000
    if s.endswith("m"):
        return int(s[:-1]) / 1_000
    return float(s)


def _parse_mem_mb(s: str) -> float:
    """Parse k8s memory string → MB (float).
    Examples: '16Gi' → 16384, '512Mi' → 512, '1000Ki' → ~0.977
    """
    units = {
        "Ki": 1 / 1024,
        "Mi": 1,
        "Gi": 1024,
        "Ti": 1024 ** 2,
        "K": 1 / 1000,
        "M": 1,
        "G": 1000,
    }
    for unit, factor in units.items():
        if s.endswith(unit):
            return float(s[: -len(unit)]) * factor
    return float(s) / 1_048_576  # assume raw bytes


def _fetch_node_temp(url: str) -> float | None:
    """Fetch CPU temperature from a server-stats agent."""
    try:
        r = httpx.get(f"{url.rstrip('/')}/metrics", timeout=2.0)
        r.raise_for_status()
        data = r.json()
        return data.get("temperature", {}).get("cpu_avg")
    except Exception:
        return None


def collect_metrics() -> dict:
    v1, custom = get_clients()

    # ── Node list ──────────────────────────────────────────────
    nodes = v1.list_node()

    # ── metrics-server (actual CPU/RAM usage) ──────────────────
    try:
        node_metrics_raw = custom.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes",
        )
        metrics_map: dict[str, dict] = {
            item["metadata"]["name"]: item["usage"]
            for item in node_metrics_raw["items"]
        }
    except Exception:
        metrics_map = {}

    # ── Running pod count per node ─────────────────────────────
    pods = v1.list_pod_for_all_namespaces(field_selector="status.phase=Running")
    pod_counts: dict[str, int] = {}
    for pod in pods.items:
        node_name = pod.spec.node_name
        if node_name:
            pod_counts[node_name] = pod_counts.get(node_name, 0) + 1

    # ── Build per-node data ────────────────────────────────────
    node_list = []
    for node in nodes.items:
        name = node.metadata.name

        # Status
        conditions = {c.type: c.status for c in node.status.conditions}
        ready = conditions.get("Ready") == "True"

        # Roles  (label key = "node-role.kubernetes.io/<role>")
        labels = node.metadata.labels or {}
        roles = [k.split("/")[-1] for k in labels if "node-role.kubernetes.io/" in k]
        role = ",".join(sorted(roles)) if roles else "worker"

        # Capacity & allocatable
        capacity = node.status.capacity or {}
        allocatable = node.status.allocatable or {}
        cpu_cap = _parse_cpu(capacity.get("cpu", "0"))
        mem_cap_mb = _parse_mem_mb(capacity.get("memory", "0Ki"))
        max_pods = int(allocatable.get("pods", capacity.get("pods", 110)))

        # Actual usage from metrics-server (may be absent)
        if name in metrics_map:
            usage = metrics_map[name]
            cpu_used: float | None = _parse_cpu(usage.get("cpu", "0n"))
            mem_used_mb: float | None = _parse_mem_mb(usage.get("memory", "0Ki"))
        else:
            cpu_used = None
            mem_used_mb = None

        cpu_pct = (
            round(cpu_used / cpu_cap * 100, 1)
            if cpu_used is not None and cpu_cap > 0
            else None
        )
        mem_pct = (
            round(mem_used_mb / mem_cap_mb * 100, 1)
            if mem_used_mb is not None and mem_cap_mb > 0
            else None
        )

        running_pods = pod_counts.get(name, 0)
        pod_pct = round(running_pods / max_pods * 100, 1) if max_pods > 0 else 0

        # Optional temperature from server-stats agent
        temperature: float | None = None
        if name in NODE_STATS_URLS:
            temperature = _fetch_node_temp(NODE_STATS_URLS[name])

        # Node info
        info = node.status.node_info
        node_list.append(
            {
                "name": name,
                "ready": ready,
                "role": role,
                "kubelet_version": info.kubelet_version if info else "unknown",
                "os_image": info.os_image if info else "unknown",
                "cpu": {
                    "capacity_cores": round(cpu_cap, 2),
                    "used_cores": round(cpu_used, 3) if cpu_used is not None else None,
                    "percent": cpu_pct,
                },
                "ram": {
                    "capacity_mb": int(mem_cap_mb),
                    "used_mb": int(mem_used_mb) if mem_used_mb is not None else None,
                    "percent": mem_pct,
                },
                "pods": {
                    "running": running_pods,
                    "capacity": max_pods,
                    "percent": pod_pct,
                },
                "temperature": {"cpu_avg": temperature},
            }
        )

    ready_count = sum(1 for n in node_list if n["ready"])
    total_pods = sum(pod_counts.values())

    return {
        "cluster": {
            "total_nodes": len(node_list),
            "ready_nodes": ready_count,
            "total_pods": total_pods,
        },
        "nodes": node_list,
    }
