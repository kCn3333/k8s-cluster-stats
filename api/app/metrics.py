from app.discovery import collect_agent_data
from app.k8s_client import get_clients


def _parse_cpu(s: str) -> float:
    if s.endswith("n"):
        return int(s[:-1]) / 1_000_000_000
    if s.endswith("m"):
        return int(s[:-1]) / 1_000
    return float(s)


def _parse_mem_mb(s: str) -> float:
    units = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024 ** 2, "K": 1 / 1000, "M": 1, "G": 1000}
    for unit, factor in units.items():
        if s.endswith(unit):
            return float(s[: -len(unit)]) * factor
    return float(s) / 1_048_576


def collect_metrics() -> dict:
    v1, custom = get_clients()

    nodes = v1.list_node()

    try:
        raw = custom.list_cluster_custom_object(
            group="metrics.k8s.io", version="v1beta1", plural="nodes"
        )
        metrics_map: dict[str, dict] = {
            item["metadata"]["name"]: item["usage"] for item in raw["items"]
        }
    except Exception:
        metrics_map = {}

    pods = v1.list_pod_for_all_namespaces(field_selector="status.phase=Running")
    pod_counts: dict[str, int] = {}
    for pod in pods.items:
        n = pod.spec.node_name
        if n:
            pod_counts[n] = pod_counts.get(n, 0) + 1

    agent_data = collect_agent_data()

    node_list = []
    for node in nodes.items:
        name = node.metadata.name

        conditions = {c.type: c.status for c in node.status.conditions}
        ready = conditions.get("Ready") == "True"

        labels = node.metadata.labels or {}
        roles = [k.split("/")[-1] for k in labels if "node-role.kubernetes.io/" in k]
        role = ",".join(sorted(roles)) if roles else "worker"

        capacity = node.status.capacity or {}
        allocatable = node.status.allocatable or {}
        cpu_cap = _parse_cpu(capacity.get("cpu", "0"))
        mem_cap_mb = _parse_mem_mb(capacity.get("memory", "0Ki"))
        max_pods = int(allocatable.get("pods", capacity.get("pods", 110)))

        if name in metrics_map:
            usage = metrics_map[name]
            cpu_used: float | None = _parse_cpu(usage.get("cpu", "0n"))
            mem_used_mb: float | None = _parse_mem_mb(usage.get("memory", "0Ki"))
        else:
            cpu_used = None
            mem_used_mb = None

        cpu_pct = round(cpu_used / cpu_cap * 100, 1) if cpu_used is not None and cpu_cap > 0 else None
        mem_pct = round(mem_used_mb / mem_cap_mb * 100, 1) if mem_used_mb is not None and mem_cap_mb > 0 else None

        running_pods = pod_counts.get(name, 0)
        pod_pct = round(running_pods / max_pods * 100, 1) if max_pods > 0 else 0

        agent = agent_data.get(name, {})
        info = node.status.node_info

        node_list.append({
            "name": name,
            "ready": ready,
            "role": role,
            "kubelet_version": info.kubelet_version if info else "unknown",
            "os_image": info.os_image if info else "unknown",
            "cpu": {
                "capacity_cores": round(cpu_cap, 2),
                "used_cores": round(cpu_used, 3) if cpu_used is not None else None,
                "percent": cpu_pct,
                "load_1m": agent.get("cpu", {}).get("load_1m"),
                "load_5m": agent.get("cpu", {}).get("load_5m"),
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
            "uptime": {
                "seconds": agent.get("uptime_seconds"),
                "human": agent.get("uptime_human"),
            },
            "temperature": {
                "cpu_avg": agent.get("temperature", {}).get("cpu_avg"),
            },
        })

    ready_count = sum(1 for n in node_list if n["ready"])

    return {
        "cluster": {
            "total_nodes": len(node_list),
            "ready_nodes": ready_count,
            "total_pods": sum(pod_counts.values()),
        },
        "nodes": node_list,
    }
