# k8s-badge

Lightweight Kubernetes cluster monitoring API and SVG badge.

## Features

- Per-node stats via k8s API + metrics-server:
  - CPU usage & capacity
  - RAM usage & capacity
  - Pod count / capacity
  - Node status (Ready / NotReady)
  - Node role (control-plane / worker)
- Optional CPU temperature via [server-stats](https://github.com/kCn3333/server-stats) agents
- Live SVG badges (cluster overview + per-node)
- 15-second TTL cache — no background loops
- Read-only RBAC (nodes, pods, metrics.k8s.io)

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /metrics` | Full cluster JSON |
| `GET /metrics/{node}` | Single-node JSON |
| `GET /badge.svg` | SVG — all nodes at a glance |
| `GET /badge/{node}.svg` | SVG — single-node detail |

### Example: embed cluster badge in a README

```markdown
![cluster status](https://k8s-badge.your-domain.com/badge.svg)
```

### Example: embed per-node badge

```markdown
![node-1](https://k8s-badge.your-domain.com/badge/node-1.svg)
```

### Example JSON response (`/metrics`)

```json
{
  "cluster": {
    "total_nodes": 3,
    "ready_nodes": 3,
    "total_pods": 47
  },
  "nodes": [
    {
      "name": "node-1",
      "ready": true,
      "role": "worker",
      "kubelet_version": "v1.29.0",
      "cpu": { "capacity_cores": 8, "used_cores": 1.842, "percent": 23.0 },
      "ram": { "capacity_mb": 16090, "used_mb": 7200, "percent": 44.8 },
      "pods": { "running": 18, "capacity": 110, "percent": 16.4 },
      "temperature": { "cpu_avg": null }
    }
  ]
}
```

## Requirements

- Kubernetes cluster with **metrics-server** installed
- Image registry accessible from the cluster

## Quick start (in-cluster)

```bash
# 1. Create namespace
kubectl create namespace monitoring

# 2. Apply RBAC
kubectl apply -f k8s/rbac.yaml

# 3. Build and push your image
docker build -t your-registry/k8s-badge:latest .
docker push your-registry/k8s-badge:latest

# 4. Edit k8s/deployment.yaml — set image and ALLOWED_CORS_SUFFIX
kubectl apply -f k8s/deployment.yaml
```

## Local development (docker-compose)

```bash
# Uses your local ~/.kube/config
docker-compose up --build
```

## Optional: CPU temperature

Deploy [server-stats](https://github.com/kCn3333/server-stats) as a DaemonSet on each node
(or as a standalone container), then set `NODE_STATS_URLS`:

```
NODE_STATS_URLS=node-1=http://node-1:8000,node-2=http://node-2:8000
```

Temperature will appear in `/metrics` and in the per-node SVG badge.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `ALLOWED_CORS_SUFFIX` | _(empty)_ | Domain suffix for CORS (e.g. `.your-domain.com`) |
| `NODE_STATS_URLS` | _(empty)_ | Comma-separated `node=url` pairs for temperature |

## License

MIT
