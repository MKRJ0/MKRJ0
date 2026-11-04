#!/usr/bin/env python3
"""Build the green terminal-style profile assets.

    python3 scripts/build_assets.py contributions   # assets/contributions.svg (needs network)
    python3 scripts/build_assets.py hero PHOTO.jpg  # assets/hero.svg (needs Pillow)
"""
import datetime as dt
import html
import re
import sys
import urllib.request
from pathlib import Path

USER = "MKRJ0"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BG = "#0A0203"
PANEL = "#110405"
GREENS = ["#1F0A0C", "#4D0E15", "#801620", "#B8222F", "#FF2A3D"]  # level 0..4
FONT = "'JetBrains Mono','Fira Code','SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"


# ───────────────────────── contributions ─────────────────────────
def fetch_contributions():
    req = urllib.request.Request(
        f"https://github.com/users/{USER}/contributions",
        headers={"User-Agent": "profile-asset-builder"},
    )
    page = urllib.request.urlopen(req, timeout=30).read().decode()
    days = {}
    for m in re.finditer(r'data-date="(\d{4}-\d\d-\d\d)" id="([^"]+)"[^>]*data-level="(\d)"', page):
        days[m.group(2)] = [m.group(1), int(m.group(3)), 0]
    for m in re.finditer(r'for="([^"]+)"[^>]*>(\d+) contributions? on', page):
        if m.group(1) in days:
            days[m.group(1)][2] = int(m.group(2))
    return sorted((d, lvl, n) for d, lvl, n in days.values())


def build_contributions():
    days = fetch_contributions()
    total = sum(n for _, _, n in days)
    first = dt.date.fromisoformat(days[0][0])
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # back to Sunday

    cell, gap = 15, 4
    step = cell + gap
    x0, y0 = 70, 110
    weeks = (dt.date.fromisoformat(days[-1][0]) - start).days // 7 + 1
    width = x0 + weeks * step + 40
    height = y0 + 7 * step + 70

    rects, months, last_month = [], [], None
    for d, lvl, n in days:
        date = dt.date.fromisoformat(d)
        w = (date - start).days // 7
        r = (date.weekday() + 1) % 7
        x, y = x0 + w * step, y0 + r * step
        cls = f' class="on" style="animation-delay:{(w * 0.035):.2f}s"' if lvl else ""
        rects.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{GREENS[lvl]}"{cls}/>')
        if date.day <= 7 and date.month != last_month and r == 0:
            months.append(f'<text x="{x}" y="{y0 - 12}">{date.strftime("%b")}</text>')
            last_month = date.month

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{total} contributions in the last year">
  <style>
    text {{ font-family: {FONT}; }}
    .on {{ animation: glow 3.2s ease-in-out infinite; }}
    @keyframes glow {{ 0%,100% {{ filter: none }} 50% {{ filter: brightness(1.6) drop-shadow(0 0 4px #FF2A3D) }} }}
    .cur {{ animation: blink 1s steps(1) infinite; }}
    @keyframes blink {{ 50% {{ opacity: 0 }} }}
  </style>
  <rect width="{width}" height="{height}" rx="16" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="16" fill="none" stroke="#FF2A3D" stroke-opacity=".25"/>
  <text x="{x0 - 40}" y="52" font-size="26" font-weight="700" fill="#FF2A3D">{total:,} contributions <tspan fill="#E8828A" font-weight="400">in the last year</tspan></text>
  <text x="{width - 40}" y="52" font-size="14" fill="#B8434C" text-anchor="end">@{USER}</text>
  <g font-size="13" fill="#B8434C">{"".join(months)}</g>
  <g font-size="12" fill="#B8434C"><text x="{x0 - 40}" y="{y0 + step + 12}">Mon</text><text x="{x0 - 40}" y="{y0 + 3 * step + 12}">Wed</text><text x="{x0 - 40}" y="{y0 + 5 * step + 12}">Fri</text></g>
  {"".join(rects)}
  <text x="{x0 - 40}" y="{height - 26}" font-size="13" fill="#B8434C">&gt; github activity tracking // contribution stream online<tspan class="cur" fill="#FF2A3D"> █</tspan></text>
  <g transform="translate({width - 40 - 5 * step - 80},{height - 38})" font-size="12" fill="#B8434C">
    <text x="0" y="12">Less</text>
    {"".join(f'<rect x="{40 + i * step}" y="0" width="{cell}" height="{cell}" rx="3" fill="{c}"/>' for i, c in enumerate(GREENS))}
    <text x="{44 + 5 * step}" y="12">More</text>
  </g>
</svg>'''
    (ASSETS / "contributions.svg").write_text(svg)
    print(f"contributions.svg: {total} contributions, {weeks} weeks")
    build_stats(days)


# ───────────────────────── stats card ─────────────────────────
def api(path):
    import json, os
    headers = {"User-Agent": "profile-asset-builder", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    return json.load(urllib.request.urlopen(req, timeout=30))


def build_stats(days):
    user = api(f"/users/{USER}")
    repos = [r for r in api(f"/users/{USER}/repos?per_page=100") if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in repos)
    langs = {}
    for r in repos:
        for k, v in api(f"/repos/{USER}/{r['name']}/languages").items():
            langs[k] = langs.get(k, 0) + v
    total_bytes = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]

    total = sum(n for _, _, n in days)
    longest = cur = run = 0
    for _, _, n in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    for _, _, n in reversed(days):
        if n:
            cur += 1
        elif cur or _ != days[-1][0]:
            break
    active = sum(1 for _, _, n in days if n)

    W, H = 1200, 300
    rows = [
        ("contributions", f"{total:,}"), ("active days", str(active)),
        ("current streak", f"{cur}d"), ("longest streak", f"{longest}d"),
        ("public repos", str(user["public_repos"])), ("stars earned", str(stars)),
        ("followers", str(user["followers"])), ("member since", user["created_at"][:4]),
    ]
    tiles = []
    for i, (k, v) in enumerate(rows):
        x, y = 50 + (i % 4) * 160, 92 + (i // 4) * 96
        tiles.append(
            f'<text x="{x}" y="{y + 34}" font-size="34" font-weight="800" fill="#FF2A3D">{v}</text>'
            f'<text x="{x}" y="{y + 60}" font-size="13" fill="#B8434C">{k}</text>'
        )
    bars, lx = [], 740
    for i, (name, b) in enumerate(top):
        pct = b / total_bytes
        y = 100 + i * 36
        bars.append(
            f'<text x="{lx}" y="{y + 12}" font-size="14" fill="#FFC9CE">{html.escape(name)}</text>'
            f'<rect x="{lx + 130}" y="{y}" width="240" height="14" rx="2" fill="#1F0A0C"/>'
            f'<rect x="{lx + 130}" y="{y}" width="{max(4, 240 * pct):.0f}" height="14" rx="2" fill="{GREENS[4 - min(i, 3)]}"/>'
            f'<text x="{lx + 410}" y="{y + 12}" font-size="13" fill="#B8434C" text-anchor="end">{pct:.0%}</text>'
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub stats for {USER}">
  <style>text {{ font-family: {FONT}; }}</style>
  <rect width="{W}" height="{H}" rx="16" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#FF2A3D" stroke-opacity=".25"/>
  <text x="50" y="56" font-size="18" fill="#FF2A3D"><tspan fill="#B8434C">$</tspan> git log --stats <tspan fill="#B8434C">--author={USER}</tspan></text>
  <text x="{lx}" y="56" font-size="18" fill="#FF2A3D"><tspan fill="#B8434C">$</tspan> top-languages</text>
  <line x1="700" y1="40" x2="700" y2="{H - 40}" stroke="#FF2A3D" stroke-opacity=".2"/>
  {"".join(tiles)}
  {"".join(bars)}
</svg>"""
    (ASSETS / "stats.svg").write_text(svg)
    print(f"stats.svg: {total} contributions, streak {cur}/{longest}, langs {[k for k, _ in top]}")


# ───────────────────────── hero / portrait ─────────────────────────
PORTRAIT_GREENS = ["#0A0203", "#200507", "#33080B", "#470C10", "#5C1016", "#72151C", "#891B22", "#A1222A", "#BA2B33", "#D43A40", "#EA5C60", "#FA8C8E", "#FFC2C2", "#FFF0F0"]


def portrait_paths(photo, ox, oy, cols, rows, px):
    """Render a head-and-shoulders photo as a green phosphor pixel portrait."""
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    im = Image.open(photo).convert("RGB")
    w, h = im.size
    # crop head + shoulders to the panel aspect ratio, anchored near the top
    cw = int(w * 0.88)
    ch = int(cw * rows / cols)
    left = (w - cw) // 2 - int(w * 0.02)
    top = int(h * 0.07)
    im = im.crop((left, top, left + cw, top + ch))
    # weight green/blue heavily so the red studio backdrop drops to black
    r, g, b = im.split()
    lum = Image.merge("RGB", (r, g, b)).convert("L", (0.10, 0.75, 0.15, 0))
    lum = ImageOps.autocontrast(lum, cutoff=1)
    lum = ImageEnhance.Contrast(lum).enhance(1.25)
    lum = lum.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=1))
    small = lum.resize((cols, rows), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=0))

    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    levels = len(PORTRAIT_GREENS) - 1
    paths = {i: [] for i in range(1, levels + 1)}
    for y in range(rows):
        run_lvl, run_start = 0, 0
        for x in range(cols + 1):
            if x < cols:
                v = (small.getpixel((x, y)) / 255) ** 0.9
                t = 0
                lvl = max(0, min(levels, int(v * levels + t + 0.5)))
            else:
                lvl = -1
            if lvl != run_lvl or x == cols:
                if run_lvl > 0:
                    n = x - run_start
                    paths[run_lvl].append(f"M{ox + run_start * px:g} {oy + y * px:g}h{n * px:g}v{px:g}h-{n * px:g}z")
                run_lvl, run_start = lvl, x
    return "".join(
        f'<path fill="{PORTRAIT_GREENS[l]}" d="{"".join(p)}"/>' for l, p in paths.items() if p
    )


def portrait_image(photo, ox, oy, pw, ph):
    """Embed the photo in full colour, cropped to head + shoulders."""
    import base64, io
    from PIL import Image
    im = Image.open(photo).convert("RGB")
    w, h = im.size
    cw = int(w * 0.88)
    ch = int(cw * ph / pw)
    left = (w - cw) // 2 - int(w * 0.02)
    top = int(h * 0.07)
    im = im.crop((left, top, left + cw, top + ch)).resize((int(pw * 2), int(ph * 2)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=86, optimize=True, progressive=True)
    data = base64.b64encode(buf.getvalue()).decode()
    return f'<image x="{ox}" y="{oy}" width="{pw}" height="{ph}" href="data:image/jpeg;base64,{data}"/>'


def build_hero(photo):
    W, H = 1200, 440
    px, cols, rows = 2, 160, 175
    pw, ph = cols * px, rows * px
    ox, oy = W - pw - 70, 46
    portrait = portrait_paths(photo, ox, oy, cols, rows, px)

    chips = ["React", "Node.js", "TypeScript", "Docker", "AI / RAG"]
    cx, chip_svg = 70, []
    for c in chips:
        w = 22 + len(c) * 10
        chip_svg.append(
            f'<rect x="{cx}" y="268" width="{w}" height="34" rx="4" fill="#FF2A3D" fill-opacity=".06" stroke="#FF2A3D" stroke-width="1.5"/>'
            f'<text x="{cx + w / 2}" y="290" text-anchor="middle" font-size="15" font-weight="700" fill="#FF2A3D">{html.escape(c)}</text>'
        )
        cx += w + 12

    # first-load reveal: the scan line uncovers the portrait once, the tag counts up to COMPLETE.
    # Base styles are the FINAL state, so renderers without CSS animation show the finished portrait.
    D, T, N = 0.6, 3.6, 10
    load_css, load_svg = [], []
    for i in range(N):
        a, b = i * 100 / N, (i + 1) * 100 / N
        frames = (f"0%,{b - .01:.2f}% {{{{ opacity: 1 }}}}" if i == 0 else
                  f"0%,{a - .01:.2f}% {{{{ opacity: 0 }}}} {a:.2f}%,{b - .01:.2f}% {{{{ opacity: 1 }}}}") + f" {b:.2f}%,100% {{{{ opacity: 0 }}}}"
        load_css.append(f".l{i} {{{{ opacity: 0; animation: l{i} {T}s linear {D}s 1 both; }}}} @keyframes l{i} {{{{ {frames} }}}}")
        load_svg.append(f'<text class="l{i}" x="{ox + pw - 8}" y="{oy - 8}" font-size="12" font-weight="800" fill="#FF2A3D" text-anchor="end" letter-spacing="2">LOADING {round(i * 100 / N)}%</text>')
    load_css = "\n      ".join(load_css).replace("{{", "{").replace("}}", "}")
    load_svg = "\n    ".join(load_svg)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="MKRJ — Full Stack Developer">
  <defs>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".16"/></pattern>
    <radialGradient id="vig" cx=".5" cy=".5" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></radialGradient>
    <filter id="glow" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <linearGradient id="trail" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FF2A3D" stop-opacity="0"/><stop offset="1" stop-color="#FF2A3D" stop-opacity=".22"/></linearGradient>
    <linearGradient id="beamline" x1="0" x2="1"><stop offset="0" stop-color="#FF8F99" stop-opacity="0"/><stop offset=".15" stop-color="#FFD3D7"/><stop offset=".85" stop-color="#FFD3D7"/><stop offset="1" stop-color="#FF8F99" stop-opacity="0"/></linearGradient>
    <filter id="beamglow" x="-5%" y="-400%" width="110%" height="900%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="16"/></clipPath>
    <pattern id="grid" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="2" height="2" fill="#FF2A3D" opacity=".10"/></pattern>
    <clipPath id="pclip"><rect x="{ox}" y="{oy}" width="{pw}" height="{ph}"/></clipPath>
    <style>
      text {{ font-family: {FONT}; }}
      .cur {{ animation: blink 1s steps(1) infinite; }}
      @keyframes blink {{ 50% {{ opacity: 0 }} }}
      .cover {{ transform: translateY({ph}px); animation: reveal {T}s linear {D}s 1 both; }}
      @keyframes reveal {{ from {{ transform: translateY(0) }} to {{ transform: translateY({ph}px) }} }}
      .beam {{ opacity: 0; animation: beamin {T}s linear {D}s 1 both; }}
      @keyframes beamin {{ 0% {{ transform: translateY(0); opacity: 1 }} 97% {{ transform: translateY({ph}px); opacity: 1 }} 100% {{ transform: translateY({ph}px); opacity: 0 }} }}
      @keyframes beam {{ 0% {{ transform: translateY(0); opacity: 0 }} 8% {{ opacity: 1 }} 62% {{ transform: translateY({ph}px); opacity: 1 }} 70%,100% {{ transform: translateY({ph}px); opacity: 0 }} }}
      .ldg {{ opacity: 0; animation: ldg {T}s linear {D}s 1 both; }}
      @keyframes ldg {{ 0%,99.9% {{ opacity: 1 }} 100% {{ opacity: 0 }} }}
      .done {{ opacity: 1; animation: done {T}s linear {D}s 1 both; }}
      @keyframes done {{ 0%,99.9% {{ opacity: 0 }} 100% {{ opacity: 1 }} }}
      {load_css}
      .flick {{ animation: flick 6s steps(1) infinite; }}
      @keyframes flick {{ 0%,95%,100% {{ opacity: 1 }} 96% {{ opacity: .55 }} 97% {{ opacity: 1 }} 98% {{ opacity: .7 }} }}
      .pulse {{ animation: pulse 2s ease-in-out infinite; }}
      @keyframes pulse {{ 50% {{ opacity: .3 }} }}
    </style>
  </defs>
  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="{BG}"/>

    <!-- left: identity -->
    <text x="70" y="86" font-size="14" fill="#B8434C" letter-spacing="3">&gt; HELLO, WORLD</text>
    <g class="flick" filter="url(#glow)">
      <text x="64" y="178" font-size="104" font-weight="800" fill="#FF2A3D" letter-spacing="4">MKRJ<tspan class="cur">_</tspan></text>
    </g>
    <text x="70" y="226" font-size="19" font-weight="700" fill="#FFC9CE">Full Stack Developer <tspan fill="#B8434C">|</tspan> Backend Engineer <tspan fill="#B8434C">|</tspan> AI Builder</text>
    {"".join(chip_svg)}
    <text x="70" y="350" font-size="16" fill="#E8828A"><tspan fill="#FF2A3D">$</tspan> ships → production web apps, booking &amp; payment systems, AI workflows</text>
    <circle class="pulse" cx="76" cy="389" r="5" fill="#FF2A3D"/>
    <text x="90" y="394" font-size="14" fill="#B8434C">Tehran, IR  ·  open to work  ·  github.com/{USER}</text>

    <rect width="{W}" height="{H}" fill="url(#vig)"/>

    <!-- right: portrait -->
    <rect x="{ox - 12}" y="{oy - 12}" width="{pw + 24}" height="{ph + 24}" fill="{PANEL}" stroke="#FF2A3D" stroke-opacity=".35"/>
    <g clip-path="url(#pclip)" shape-rendering="crispEdges">
      <rect x="{ox}" y="{oy}" width="{pw}" height="{ph}" fill="{PORTRAIT_GREENS[0]}"/>
      {portrait}
      <g class="cover">
        <rect x="{ox}" y="{oy}" width="{pw}" height="{ph}" fill="{PORTRAIT_GREENS[0]}"/>
        <rect x="{ox}" y="{oy}" width="{pw}" height="{ph}" fill="url(#grid)"/>
      </g>
      <g class="beam" style="mix-blend-mode:screen">
        <rect x="{ox}" y="{oy - 70}" width="{pw}" height="70" fill="url(#trail)"/>
        <rect x="{ox}" y="{oy - 3}" width="{pw}" height="3" fill="url(#beamline)" filter="url(#beamglow)"/>
      </g>
    </g>
    <g class="done">
      <rect x="{ox + pw - 96}" y="{oy - 24}" width="96" height="22" fill="#FF2A3D"/>
      <text x="{ox + pw - 48}" y="{oy - 8}" font-size="12" font-weight="800" fill="{BG}" text-anchor="middle" letter-spacing="2">COMPLETE</text>
      <text x="{ox}" y="{oy + ph + 30}" font-size="12" fill="#B8434C">&gt; portrait.svg loaded // terminal profile</text>
    </g>
    <g class="ldg">
      <rect x="{ox + pw - 140}" y="{oy - 24}" width="140" height="22" fill="{BG}" stroke="#FF2A3D"/>
      <text x="{ox}" y="{oy + ph + 30}" font-size="12" fill="#B8434C">&gt; scanning portrait.svg ...<tspan class="cur" fill="#FF2A3D"> █</tspan></text>
    </g>
    {load_svg}

  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#FF2A3D" stroke-opacity=".25"/>
</svg>'''
    (ASSETS / "hero.svg").write_text(svg)
    print(f"hero.svg: {len(svg) // 1024} KB")


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    if sys.argv[1:2] == ["contributions"]:
        build_contributions()
    elif sys.argv[1:2] == ["hero"] and len(sys.argv) == 3:
        build_hero(sys.argv[2])
    else:
        sys.exit(__doc__)
