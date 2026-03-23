import json
import os

from fastapi import FastAPI, HTTPException, Request, Response

from app.cache import metrics_cache
from app.metrics import collect_metrics
from app.svg import render_cluster_badge, render_node_badge

app = FastAPI(title="k8s-badge", version="1.0.0")

ALLOWED_CORS_SUFFIX = os.getenv("ALLOWED_CORS_SUFFIX", "")

CACHE_HEADERS = {
    "Cache-Control": "public, s-maxage=15, max-age=15",
}


def _cors_headers(request: Request) -> dict[str, str]:
    """Return CORS headers when the origin matches the configured suffix."""
    origin = request.headers.get("origin", "")
    if ALLOWED_CORS_SUFFIX and origin.endswith(ALLOWED_CORS_SUFFIX):
        return {
            "Access-Control-Allow-Origin": origin,
            "Vary": "Origin",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
        }
    return {}


def _get_metrics() -> dict:
    if "data" not in metrics_cache:
        metrics_cache["data"] = collect_metrics()
    return metrics_cache["data"]


# ── /metrics ───────────────────────────────────────────────────────────────────
@app.get("/metrics")
def metrics(request: Request) -> Response:
    """Full cluster metrics in JSON."""
    data = _get_metrics()
    headers = {**CACHE_HEADERS, "Content-Type": "application/json", **_cors_headers(request)}
    return Response(content=json.dumps(data, indent=2), headers=headers, media_type="application/json")


# ── /metrics/{node} ────────────────────────────────────────────────────────────
@app.get("/metrics/{node_name}")
def metrics_node(node_name: str, request: Request) -> Response:
    """Single-node metrics in JSON."""
    data = _get_metrics()
    node = next((n for n in data["nodes"] if n["name"] == node_name), None)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_name}' not found")
    headers = {**CACHE_HEADERS, "Content-Type": "application/json", **_cors_headers(request)}
    return Response(content=json.dumps(node, indent=2), headers=headers, media_type="application/json")


# ── /badge.svg ─────────────────────────────────────────────────────────────────
@app.get("/badge.svg")
def badge_cluster(request: Request) -> Response:
    """SVG badge — all nodes at a glance."""
    data = _get_metrics()
    svg = render_cluster_badge(data)
    headers = {**CACHE_HEADERS, "X-Frame-Options": "ALLOWALL", **_cors_headers(request)}
    return Response(content=svg, headers=headers, media_type="image/svg+xml")


# ── /badge/{node}.svg ──────────────────────────────────────────────────────────
@app.get("/badge/{node_name}.svg")
def badge_node(node_name: str, request: Request) -> Response:
    """SVG badge — single node detail."""
    data = _get_metrics()
    node = next((n for n in data["nodes"] if n["name"] == node_name), None)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_name}' not found")
    svg = render_node_badge(node)
    headers = {**CACHE_HEADERS, "X-Frame-Options": "ALLOWALL", **_cors_headers(request)}
    return Response(content=svg, headers=headers, media_type="image/svg+xml")
