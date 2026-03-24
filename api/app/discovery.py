import os

import httpx

from app.k8s_client import get_clients

AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))
AGENT_LABEL = os.getenv("AGENT_LABEL_SELECTOR", "app.kubernetes.io/component=agent,app.kubernetes.io/name=k8s-badge")
AGENT_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "2.0"))


def _get_agent_namespace() -> str:
    """Read current namespace from service-account file (works in-cluster)."""
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            return f.read().strip()
    except OSError:
        return os.getenv("AGENT_NAMESPACE", "monitoring")


def _fetch_one(pod_ip: str) -> dict | None:
    try:
        r = httpx.get(
            f"http://{pod_ip}:{AGENT_PORT}/metrics",
            timeout=AGENT_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def collect_agent_data() -> dict[str, dict]:
    """Return a mapping of node_name → agent metrics dict."""
    v1, _ = get_clients()
    namespace = _get_agent_namespace()

    try:
        pods = v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=AGENT_LABEL,
        )
    except Exception:
        return {}

    result: dict[str, dict] = {}
    for pod in pods.items:
        if pod.status.phase != "Running":
            continue
        pod_ip = pod.status.pod_ip
        node_name = pod.spec.node_name
        if not pod_ip or not node_name:
            continue
        data = _fetch_one(pod_ip)
        if data:
            result[node_name] = data

    return result
