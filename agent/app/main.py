import json

from cachetools import TTLCache
from fastapi import FastAPI, Response

from app.metrics import collect

app = FastAPI(title="k8s-badge-agent")

_cache: TTLCache = TTLCache(maxsize=1, ttl=15)

HEADERS = {
    "Cache-Control": "public, s-maxage=15, max-age=15",
    "Content-Type": "application/json",
}


@app.get("/metrics")
def metrics() -> Response:
    if "data" not in _cache:
        _cache["data"] = collect()
    return Response(
        content=json.dumps(_cache["data"]),
        headers=HEADERS,
        media_type="application/json",
    )


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
