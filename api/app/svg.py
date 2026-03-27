# ──────────────────────────────────────────────────────────────────────────────
# SVG badge renderer
# ──────────────────────────────────────────────────────────────────────────────

# ── STYLE ─────────────────────────────────────────────────────────────────────
FONT        = "Consolas, 'Liberation Mono', Menlo, Courier, monospace"
BG          = "#0d1117"   # tło badge'a
BORDER      = "#30363d"   # kolor ramki
SEPARATOR   = "#21262d"   # linia oddzielająca header od wierszy
BAR_TRACK   = "#21262d"   # tło paska postępu
TEXT_DIM    = "#4a5568"   # etykiety (CPU / RAM / TEMP)
TEXT_MID    = "#8b949e"   # wartości drugorzędne
TEXT_BRIGHT = "#c9d1d9"   # wartości główne (nazwa noda)

# Progi kolorowania (zielony → żółty → czerwony)
WARN_CPU    = 70   # % CPU powyżej którego żółty
CRIT_CPU    = 85
WARN_RAM    = 75
CRIT_RAM    = 90
WARN_TEMP   = 55   # °C
CRIT_TEMP   = 75

# Rozmiary
CORNER_R    = 12   # zaokrąglenie rogów badge'a
DOT_R       = 4    # promień kropki statusu
BAR_H       = 8    # wysokość paska postępu
BAR_R       = 4    # zaokrąglenie paska


# ── HELPERS ───────────────────────────────────────────────────────────────────
def _color(value: float | None, warn: float, crit: float) -> str:
    """Zwraca kolor hex zależny od wartości."""
    if value is None:
        return TEXT_DIM
    if value < warn:
        return "#2ecc71"   # zielony
    if value < crit:
        return "#f1c40f"   # żółty
    return "#e74c3c"       # czerwony


def _bar(x: int, cy: int, pct: float | None, width: int, warn: float = WARN_CPU, crit: float = CRIT_CPU) -> str:
    """Pasek postępu wycentrowany względem cy (środek wiersza)."""
    val  = min(100, max(0, pct or 0))
    fill = int(val * width / 100)
    col  = _color(pct, warn, crit)
    top  = cy - BAR_H // 2
    return (
        f'<rect x="{x}" y="{top}" width="{width}" height="{BAR_H}" rx="{BAR_R}" fill="{BAR_TRACK}"/>'
        f'<rect x="{x}" y="{top}" width="{fill}" height="{BAR_H}" rx="{BAR_R}" fill="{col}"/>'
    )


def _fmt(value: float | None, suffix: str = "%") -> str:
    return f"{value}{suffix}" if value is not None else "N/A"


# ── CLUSTER BADGE ─────────────────────────────────────────────────────────────
def render_cluster_badge(metrics: dict) -> str:
    """
    Badge z wierszem na każdy node.

    LAYOUT (W=720):
    [dot][name · role]  [CPU][===][%]  [RAM][===][%]  [TEMP][°C]  [pods]
    """
    cluster = metrics["cluster"]
    nodes   = metrics["nodes"]

    # ── LAYOUT ────────────────────────────────────────────────────────────────
    W        = 720    # szerokość badge'a
    ROW_H    = 36     # wysokość wiersza noda
    HEADER_H = 46     # wysokość headera — bez wiersza nagłówków kolumn
    BAR_W    = 90     # szerokość pasków CPU i RAM

    X_DOT    = 16
    X_NAME   = 32     # nazwa noda + rola

    X_CPU_L  = 210    # etykieta "CPU"
    X_CPU_B  = 232    # pasek CPU  (kończy się X_CPU_B + BAR_W = 322)
    X_CPU_T  = 330    # wartość %

    X_RAM_L  = 378    # etykieta "RAM"
    X_RAM_B  = 400    # pasek RAM  (kończy się 490)
    X_RAM_T  = 498    # wartość %

    X_TEMP_L = 548    # etykieta "TEMP"
    X_TEMP_T = 584    # wartość °C

    X_PODS   = 664    # liczba podów — wyrównana z headerem klastra
    # ──────────────────────────────────────────────────────────────────────────

    # Dane sumaryczne klastra wyliczane z nodów
    k8s_version  = nodes[0].get("kubelet_version", "") if nodes else ""
    total_cores  = int(sum(n["cpu"]["capacity_cores"] for n in nodes))
    total_ram_gb = round(sum(n["ram"]["capacity_mb"] for n in nodes) / 1024)

    HEIGHT = HEADER_H + len(nodes) * ROW_H + 14

    rows = []
    for node in nodes:
        idx = nodes.index(node)
        y   = HEADER_H + idx * ROW_H
        cy  = y + ROW_H // 2

        ready  = node["ready"]
        sc     = "#2ecc71" if ready else "#e74c3c"
        cpu    = node["cpu"]
        ram    = node["ram"]
        pods   = node["pods"]
        temp   = (node.get("temperature") or {}).get("cpu_avg")
        tc     = _color(temp, WARN_TEMP, CRIT_TEMP)

        name     = node["name"][:22]
        role     = node["role"]
        role_tag = f" · {role}" if role and role != "worker" else ""

        # Separator między wierszami (poza ostatnim)
        sep = (f'<line x1="8" y1="{y + ROW_H - 1}" x2="{W - 8}" y2="{y + ROW_H - 1}"'
               f' stroke="{SEPARATOR}" stroke-width="0.5"/>'
               if idx < len(nodes) - 1 else "")

        # Dot —  dioda klastra w headerze miga
        rows.append(f"""
  <!-- ── node: {name} ── -->
  <circle cx="{X_DOT}" cy="{cy}" r="{DOT_R}" fill="{sc}"/>
  <text x="{X_NAME}" y="{cy + 4}" fill="{TEXT_BRIGHT}" font-size="12">{name}</text>
  <text x="{X_NAME + len(name) * 7 + 4}" y="{cy + 4}" fill="{TEXT_DIM}" font-size="10">{role_tag}</text>
  <text x="{X_CPU_L}" y="{cy + 4}" fill="{TEXT_DIM}" font-size="10">CPU</text>
  {_bar(X_CPU_B, cy, cpu["percent"], BAR_W, WARN_CPU, CRIT_CPU)}
  <text x="{X_CPU_T}" y="{cy + 4}" fill="{_color(cpu['percent'], WARN_CPU, CRIT_CPU)}" font-size="11">{_fmt(cpu['percent'])}</text>
  <text x="{X_RAM_L}" y="{cy + 4}" fill="{TEXT_DIM}" font-size="10">RAM</text>
  {_bar(X_RAM_B, cy, ram["percent"], BAR_W, WARN_RAM, CRIT_RAM)}
  <text x="{X_RAM_T}" y="{cy + 4}" fill="{_color(ram['percent'], WARN_RAM, CRIT_RAM)}" font-size="11">{_fmt(ram['percent'])}</text>
  <text x="{X_TEMP_L}" y="{cy + 4}" fill="{TEXT_DIM}" font-size="10">TEMP</text>
  <text x="{X_TEMP_T}" y="{cy + 4}" fill="{tc}" font-size="11">{_fmt(temp, 'C')}</text>
  <text x="{X_PODS}" y="{cy + 4}" fill="{TEXT_MID}" font-size="11" text-anchor="middle">{pods['running']}</text>
  {sep}""")

    ready_count   = cluster["ready_nodes"]
    total_count   = cluster["total_nodes"]
    cluster_color = "#2ecc71" if ready_count == total_count else "#f1c40f" if ready_count > 0 else "#e74c3c"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{HEIGHT}" viewBox="0 0 {W} {HEIGHT}">
  <style>text {{ font-family: {FONT}; }}</style>

  <!-- Tlo i ramka -->
  <rect width="{W}" height="{HEIGHT}" rx="{CORNER_R}" fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>

  <!-- Naglowek klastra — jedna linia z pulsujaca dioda -->
  <!-- Pulsujaca dioda — TYLKO tutaj, nie przy nazwach nodow -->
  <circle cx="{X_DOT}" cy="23" r="{DOT_R}" fill="{cluster_color}">
    <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite"/>
  </circle>
  <text x="{X_NAME}" y="28" fill="{TEXT_MID}" font-size="13">k8s cluster</text>
  <text x="130" y="28" fill="{cluster_color}" font-size="13" font-weight="bold">{ready_count}/{total_count} ready</text>
  <text x="212" y="28" fill="{TEXT_DIM}" font-size="13">·</text>
  <text x="224" y="28" fill="{TEXT_MID}" font-size="12">{k8s_version}</text>
  <text x="332" y="28" fill="{TEXT_DIM}" font-size="13">·</text>
  <text x="344" y="28" fill="{TEXT_MID}" font-size="12">{total_cores} cores</text>
  <text x="412" y="28" fill="{TEXT_DIM}" font-size="13">·</text>
  <text x="424" y="28" fill="{TEXT_MID}" font-size="12">{total_ram_gb} GB</text>
  <!-- Łączna liczba podów wyrównana do kolumny pods (X_PODS={X_PODS}) -->
  <text x="{X_PODS}" y="28" fill="{TEXT_BRIGHT}" font-size="13" font-weight="bold" text-anchor="middle">{cluster['total_pods']}</text>

  <!-- Linia pod headerem — nagłówki kolumn usuniete (etykiety CPU/RAM/TEMP sa w kazdym wierszu) -->
  <line x1="8" y1="{HEADER_H - 1}" x2="{W - 8}" y2="{HEADER_H - 1}" stroke="{SEPARATOR}" stroke-width="1"/>

  {''.join(rows)}
</svg>"""


# ── PER-NODE BADGE ────────────────────────────────────────────────────────────
def render_node_badge(node: dict) -> str:
    """
    Szczegolowy badge jednego noda.

    LAYOUT (W=640):
    [dot][name]  [status]  [role]  [kubelet version]
    ─────────────────────────────────────────────────
    CPU:  [====bar====] [%]  [used/cap cores]  pods: [N]
    RAM:  [====bar====] [%]  [used/cap MB]     load: [1m]
    TEMP: [°C]   uptime: [human]
    """
    cpu    = node["cpu"]
    ram    = node["ram"]
    pods   = node["pods"]
    temp   = (node.get("temperature") or {}).get("cpu_avg")
    uptime = (node.get("uptime") or {}).get("human")

    # ── LAYOUT ────────────────────────────────────────────────────────────────
    W      = 640    # szerokość badge'a
    BAR_W  = 130    # szerokość pasków

    X_LBL  = 20    # etykiety wierszy
    X_BAR  = 60    # pasek (kończy się 190)
    X_PCT  = 198   # wartość %
    X_INFO = 258   # cores / MB
    X_SIDE = 548   # prawa kolumna
    # ──────────────────────────────────────────────────────────────────────────

    ready       = node["ready"]
    sc          = "#2ecc71" if ready else "#e74c3c"
    status_text = "ready" if ready else "not ready"
    tc          = _color(temp, WARN_TEMP, CRIT_TEMP)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="126" viewBox="0 0 {W} 126">
  <style>text {{ font-family: {FONT}; }}</style>

  <!-- Tlo i ramka -->
  <rect width="{W}" height="126" rx="{CORNER_R}" fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>

  <!-- Header: nazwa, status, rola, wersja kubelet -->
  <!-- Pulsujaca dioda statusu noda -->
  <circle cx="16" cy="21" r="{DOT_R}" fill="{sc}">
    <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite"/>
  </circle>
  <text x="28" y="26" fill="{TEXT_BRIGHT}" font-size="13" font-weight="bold">{node['name']}</text>
  <text x="190" y="26" fill="{sc}" font-size="12">{status_text}</text>
  <text x="310" y="26" fill="{TEXT_DIM}" font-size="11">{node['role']}</text>
  <text x="490" y="26" fill="{TEXT_DIM}" font-size="11">{node.get('kubelet_version', '')}</text>

  <!-- Linia separatora -->
  <line x1="8" y1="35" x2="{W - 8}" y2="35" stroke="{SEPARATOR}" stroke-width="1"/>

  <!-- CPU -->
  <text x="{X_LBL}" y="57" fill="{TEXT_MID}" font-size="12">CPU</text>
  {_bar(X_BAR, 53, cpu["percent"], BAR_W, WARN_CPU, CRIT_CPU)}
  <text x="{X_PCT}" y="57" fill="{_color(cpu['percent'], WARN_CPU, CRIT_CPU)}" font-size="12">{_fmt(cpu['percent'])}</text>
  <text x="{X_INFO}" y="57" fill="{TEXT_DIM}" font-size="11">{cpu.get('used_cores', '?')} / {cpu['capacity_cores']} cores</text>
  <text x="{X_SIDE}" y="57" fill="{TEXT_DIM}" font-size="11">pods</text>
  <text x="{X_SIDE + 40}" y="57" fill="{TEXT_BRIGHT}" font-size="12" font-weight="bold">{pods['running']}</text>

  <!-- RAM -->
  <text x="{X_LBL}" y="83" fill="{TEXT_MID}" font-size="12">RAM</text>
  {_bar(X_BAR, 79, ram["percent"], BAR_W, WARN_RAM, CRIT_RAM)}
  <text x="{X_PCT}" y="83" fill="{_color(ram['percent'], WARN_RAM, CRIT_RAM)}" font-size="12">{_fmt(ram['percent'])}</text>
  <text x="{X_INFO}" y="83" fill="{TEXT_DIM}" font-size="11">{ram.get('used_mb', '?')} / {ram['capacity_mb']} MB</text>
  <text x="{X_SIDE}" y="83" fill="{TEXT_DIM}" font-size="11">load</text>
  <text x="{X_SIDE + 40}" y="83" fill="{TEXT_MID}" font-size="11">{cpu.get('load_1m', '—')}</text>

  <!-- TEMP + uptime (oddzielny wiersz, nie nachodzi na RAM) -->
  <text x="{X_LBL}" y="109" fill="{TEXT_MID}" font-size="12">TEMP</text>
  <text x="{X_BAR}" y="109" fill="{tc}" font-size="12" font-weight="bold">{_fmt(temp, 'C')}</text>
  <text x="{X_INFO}" y="109" fill="{TEXT_DIM}" font-size="11">uptime</text>
  <text x="{X_INFO + 56}" y="109" fill="{TEXT_MID}" font-size="11">{uptime or '—'}</text>
</svg>"""