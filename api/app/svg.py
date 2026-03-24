FONT = "Consolas, 'Liberation Mono', Menlo, Courier, monospace"

# Colour thresholds (green → yellow → red)
def _color(value: float | None, warn: float = 70, crit: float = 85) -> str:
    if value is None:
        return "#4a5568"
    if value < warn:
        return "#2ecc71"
    if value < crit:
        return "#f1c40f"
    return "#e74c3c"


def _bar(x: int, y: int, pct: float | None, width: int = 72) -> str:
    """Horizontal progress bar."""
    val = min(100, max(0, pct or 0))
    fill = int(val * width / 100)
    color = _color(pct)
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="8" rx="4" fill="#21262d"/>'
        f'<rect x="{x}" y="{y}" width="{fill}" height="8" rx="4" fill="{color}"/>'
    )


def _pct_label(value: float | None) -> str:
    return f"{value}%" if value is not None else "N/A"


# ── Cluster badge ──────────────────────────────────────────────────────────────
def render_cluster_badge(metrics: dict) -> str:
    cluster = metrics["cluster"]
    nodes = metrics["nodes"]

    ROW_H = 32
    HEADER_H = 56
    W = 540

    # Column X positions
    X_DOT   = 16
    X_NAME  = 28
    X_CPU_L = 178   # "CPU" label
    X_CPU_B = 204   # bar start
    X_CPU_T = 282   # % text
    X_RAM_L = 315
    X_RAM_B = 341
    X_RAM_T = 419
    X_PODS  = 458

    HEIGHT = HEADER_H + len(nodes) * ROW_H + 16

    rows = []
    for i, node in enumerate(nodes):
        y = HEADER_H + i * ROW_H
        cy = y + ROW_H // 2

        sc = "#2ecc71" if node["ready"] else "#e74c3c"
        cpu = node["cpu"]
        ram = node["ram"]
        pods = node["pods"]

        name = node["name"][:20]
        role_tag = f'[{node["role"]}]' if node["role"] != "worker" else ""

        # Animate the dot for the first ready node only
        anim = (
            '<animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite"/>'
            if i == 0 and node["ready"]
            else ""
        )

        row = f"""
  <circle cx="{X_DOT}" cy="{cy}" r="4" fill="{sc}">{anim}</circle>
  <text x="{X_NAME}" y="{cy + 4}" fill="#c9d1d9" font-size="12">{name}</text>
  <text x="168" y="{cy + 4}" fill="#4a5568" font-size="10">{role_tag}</text>
  <text x="{X_CPU_L}" y="{cy + 4}" fill="#4a5568" font-size="10">CPU</text>
  {_bar(X_CPU_B, cy - 4, cpu["percent"])}
  <text x="{X_CPU_T}" y="{cy + 4}" fill="{_color(cpu['percent'])}" font-size="11">{_pct_label(cpu['percent'])}</text>
  <text x="{X_RAM_L}" y="{cy + 4}" fill="#4a5568" font-size="10">RAM</text>
  {_bar(X_RAM_B, cy - 4, ram["percent"])}
  <text x="{X_RAM_T}" y="{cy + 4}" fill="{_color(ram['percent'])}" font-size="11">{_pct_label(ram['percent'])}</text>
  <text x="{X_PODS}" y="{cy + 4}" fill="#8b949e" font-size="11">{pods['running']}/{pods['capacity']}</text>"""
        rows.append(row)

    ready = cluster["ready_nodes"]
    total = cluster["total_nodes"]
    cluster_color = "#2ecc71" if ready == total else "#f1c40f" if ready > 0 else "#e74c3c"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{HEIGHT}" viewBox="0 0 {W} {HEIGHT}">
  <style>text {{ font-family: {FONT}; }}</style>
  <rect width="{W}" height="{HEIGHT}" rx="12" fill="#0d1117" stroke="#30363d" stroke-width="1.5"/>

  <!-- Header -->
  <circle cx="16" cy="26" r="4" fill="{cluster_color}">
    <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite"/>
  </circle>
  <text x="28" y="31" fill="#8b949e" font-size="13">k8s cluster</text>
  <text x="125" y="31" fill="{cluster_color}" font-size="13" font-weight="bold">{ready}/{total} nodes ready</text>
  <text x="310" y="31" fill="#8b949e" font-size="13">·</text>
  <text x="324" y="31" fill="#c9d1d9" font-size="13" font-weight="bold">{cluster['total_pods']}</text>
  <text x="355" y="31" fill="#8b949e" font-size="13">pods running</text>

  <!-- Column headers -->
  <text x="{X_CPU_B}" y="50" fill="#4a5568" font-size="10">CPU</text>
  <text x="{X_RAM_B}" y="50" fill="#4a5568" font-size="10">RAM</text>
  <text x="{X_PODS}" y="50" fill="#4a5568" font-size="10">pods</text>
  <line x1="8" y1="{HEADER_H - 2}" x2="{W - 8}" y2="{HEADER_H - 2}" stroke="#21262d" stroke-width="1"/>

  {''.join(rows)}
</svg>"""


# ── Per-node badge ─────────────────────────────────────────────────────────────
def render_node_badge(node: dict) -> str:
    cpu = node["cpu"]
    ram = node["ram"]
    pods = node["pods"]
    temp = node.get("temperature", {}) or {}
    temp_val: float | None = temp.get("cpu_avg")

    W = 480
    H = 110 if temp_val is None else 130
    ready = node["ready"]
    sc = "#2ecc71" if ready else "#e74c3c"
    status_text = "ready" if ready else "not ready"

    # Optional temperature row
    temp_row = ""
    if temp_val is not None:
        tc = _color(temp_val, warn=55, crit=75)
        temp_row = f"""
  <text x="20" y="122" fill="#8b949e" font-size="12">🌡 temp</text>
  <text x="72" y="122" fill="{tc}" font-size="12" font-weight="bold">{temp_val}°C</text>"""

    anim = '<animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite"/>'

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <style>text {{ font-family: {FONT}; }}</style>
  <rect width="{W}" height="{H}" rx="12" fill="#0d1117" stroke="#30363d" stroke-width="1.5"/>

  <!-- Header row -->
  <circle cx="16" cy="22" r="4" fill="{sc}">{anim}</circle>
  <text x="28" y="27" fill="#c9d1d9" font-size="13" font-weight="bold">{node['name']}</text>
  <text x="240" y="27" fill="{sc}" font-size="12">{status_text}</text>
  <text x="340" y="27" fill="#4a5568" font-size="11">{node['role']}</text>
  <text x="390" y="27" fill="#4a5568" font-size="11">{node.get('kubelet_version', '')}</text>
  <line x1="8" y1="36" x2="{W - 8}" y2="36" stroke="#21262d" stroke-width="1"/>

  <!-- CPU row -->
  <text x="20" y="57" fill="#8b949e" font-size="12">CPU</text>
  {_bar(54, 49, cpu["percent"], 100)}
  <text x="160" y="57" fill="{_color(cpu['percent'])}" font-size="12">{_pct_label(cpu['percent'])}</text>
  <text x="215" y="57" fill="#4a5568" font-size="11">{cpu.get('used_cores', '?')} / {cpu['capacity_cores']} cores</text>
  <text x="390" y="57" fill="#8b949e" font-size="12">pods</text>
  <text x="432" y="57" fill="#c9d1d9" font-size="12" font-weight="bold">{pods['running']}</text>

  <!-- RAM row -->
  <text x="20" y="82" fill="#8b949e" font-size="12">RAM</text>
  {_bar(54, 74, ram["percent"], 100)}
  <text x="160" y="82" fill="{_color(ram['percent'])}" font-size="12">{_pct_label(ram['percent'])}</text>
  <text x="215" y="82" fill="#4a5568" font-size="11">{ram.get('used_mb', '?')} / {ram['capacity_mb']} MB</text>
  <text x="390" y="82" fill="#4a5568" font-size="11">cap: {pods['capacity']}</text>
{temp_row}
</svg>"""
