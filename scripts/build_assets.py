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

BG = "#020804"
PANEL = "#04110A"
GREENS = ["#0A1F12", "#0E4D24", "#16803A", "#22B84F", "#39FF6A"]  # level 0..4
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
    @keyframes glow {{ 0%,100% {{ filter: none }} 50% {{ filter: brightness(1.6) drop-shadow(0 0 4px #39FF6A) }} }}
    .cur {{ animation: blink 1s steps(1) infinite; }}
    @keyframes blink {{ 50% {{ opacity: 0 }} }}
  </style>
  <rect width="{width}" height="{height}" rx="16" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="16" fill="none" stroke="#39FF6A" stroke-opacity=".25"/>
  <text x="{x0 - 40}" y="52" font-size="26" font-weight="700" fill="#39FF6A">{total:,} contributions <tspan fill="#7BC98F" font-weight="400">in the last year</tspan></text>
  <text x="{width - 40}" y="52" font-size="14" fill="#2E9E52" text-anchor="end">@{USER}</text>
  <g font-size="13" fill="#2E9E52">{"".join(months)}</g>
  <g font-size="12" fill="#2E9E52"><text x="{x0 - 40}" y="{y0 + step + 12}">Mon</text><text x="{x0 - 40}" y="{y0 + 3 * step + 12}">Wed</text><text x="{x0 - 40}" y="{y0 + 5 * step + 12}">Fri</text></g>
  {"".join(rects)}
  <text x="{x0 - 40}" y="{height - 26}" font-size="13" fill="#2E9E52">&gt; github activity tracking // contribution stream online<tspan class="cur" fill="#39FF6A"> █</tspan></text>
  <g transform="translate({width - 40 - 5 * step - 80},{height - 38})" font-size="12" fill="#2E9E52">
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
            f'<text x="{x}" y="{y + 34}" font-size="34" font-weight="800" fill="#39FF6A">{v}</text>'
            f'<text x="{x}" y="{y + 60}" font-size="13" fill="#2E9E52">{k}</text>'
        )
    bars, lx = [], 740
    for i, (name, b) in enumerate(top):
        pct = b / total_bytes
        y = 100 + i * 36
        bars.append(
            f'<text x="{lx}" y="{y + 12}" font-size="14" fill="#B6FFC9">{html.escape(name)}</text>'
            f'<rect x="{lx + 130}" y="{y}" width="240" height="14" rx="2" fill="#0A1F12"/>'
            f'<rect x="{lx + 130}" y="{y}" width="{max(4, 240 * pct):.0f}" height="14" rx="2" fill="{GREENS[4 - min(i, 3)]}"/>'
            f'<text x="{lx + 410}" y="{y + 12}" font-size="13" fill="#2E9E52" text-anchor="end">{pct:.0%}</text>'
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub stats for {USER}">
  <style>text {{ font-family: {FONT}; }}</style>
  <rect width="{W}" height="{H}" rx="16" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#39FF6A" stroke-opacity=".25"/>
  <text x="50" y="56" font-size="18" fill="#39FF6A"><tspan fill="#2E9E52">$</tspan> git log --stats <tspan fill="#2E9E52">--author={USER}</tspan></text>
  <text x="{lx}" y="56" font-size="18" fill="#39FF6A"><tspan fill="#2E9E52">$</tspan> top-languages</text>
  <line x1="700" y1="40" x2="700" y2="{H - 40}" stroke="#39FF6A" stroke-opacity=".2"/>
  {"".join(tiles)}
  {"".join(bars)}
</svg>"""
    (ASSETS / "stats.svg").write_text(svg)
    print(f"stats.svg: {total} contributions, streak {cur}/{longest}, langs {[k for k, _ in top]}")


# ───────────────────────── hero / portrait ─────────────────────────
PORTRAIT_GREENS = ["#020A05", "#05200E", "#083316", "#0C471F", "#105C28", "#157232", "#1B893D", "#22A148", "#2BBA55", "#3AD465", "#5CEA82", "#8CFAA8", "#C2FFD2", "#F0FFF4"]


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
            f'<rect x="{cx}" y="268" width="{w}" height="34" rx="4" fill="#39FF6A" fill-opacity=".06" stroke="#39FF6A" stroke-width="1.5"/>'
            f'<text x="{cx + w / 2}" y="290" text-anchor="middle" font-size="15" font-weight="700" fill="#39FF6A">{html.escape(c)}</text>'
        )
        cx += w + 12

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="MKRJ — Full Stack Developer">
  <defs>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".16"/></pattern>
    <radialGradient id="vig" cx=".5" cy=".5" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></radialGradient>
    <filter id="glow" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="16"/></clipPath>
    <clipPath id="pclip"><rect x="{ox}" y="{oy}" width="{pw}" height="{ph}"/></clipPath>
    <style>
      text {{ font-family: {FONT}; }}
      .cur {{ animation: blink 1s steps(1) infinite; }}
      @keyframes blink {{ 50% {{ opacity: 0 }} }}
      .beam {{ animation: beam 4.5s linear infinite; }}
      @keyframes beam {{ from {{ transform: translateY(-40px) }} to {{ transform: translateY({ph + 40}px) }} }}
      .flick {{ animation: flick 6s steps(1) infinite; }}
      @keyframes flick {{ 0%,95%,100% {{ opacity: 1 }} 96% {{ opacity: .55 }} 97% {{ opacity: 1 }} 98% {{ opacity: .7 }} }}
      .pulse {{ animation: pulse 2s ease-in-out infinite; }}
      @keyframes pulse {{ 50% {{ opacity: .3 }} }}
    </style>
  </defs>
  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="{BG}"/>

    <!-- left: identity -->
    <text x="70" y="86" font-size="14" fill="#2E9E52" letter-spacing="3">&gt; HELLO, WORLD</text>
    <g class="flick" filter="url(#glow)">
      <text x="64" y="178" font-size="104" font-weight="800" fill="#39FF6A" letter-spacing="4">MKRJ<tspan class="cur">_</tspan></text>
    </g>
    <text x="70" y="226" font-size="19" font-weight="700" fill="#B6FFC9">Full Stack Developer <tspan fill="#2E9E52">|</tspan> Backend Engineer <tspan fill="#2E9E52">|</tspan> AI Builder</text>
    {"".join(chip_svg)}
    <text x="70" y="350" font-size="16" fill="#7BC98F"><tspan fill="#39FF6A">$</tspan> ships → production web apps, booking &amp; payment systems, AI workflows</text>
    <circle class="pulse" cx="76" cy="389" r="5" fill="#39FF6A"/>
    <text x="90" y="394" font-size="14" fill="#2E9E52">Tehran, IR  ·  open to work  ·  github.com/{USER}</text>

    <rect width="{W}" height="{H}" fill="url(#vig)"/>

    <!-- right: portrait -->
    <rect x="{ox - 12}" y="{oy - 12}" width="{pw + 24}" height="{ph + 24}" fill="{PANEL}" stroke="#39FF6A" stroke-opacity=".35"/>
    <g clip-path="url(#pclip)" shape-rendering="crispEdges">
      <rect x="{ox}" y="{oy}" width="{pw}" height="{ph}" fill="{PORTRAIT_GREENS[0]}"/>
      {portrait}
      <rect class="beam" x="{ox}" y="{oy - 30}" width="{pw}" height="18" fill="#39FF6A" opacity=".07"/>
    </g>
    <rect x="{ox + pw - 96}" y="{oy - 24}" width="96" height="22" fill="#39FF6A"/>
    <text x="{ox + pw - 48}" y="{oy - 8}" font-size="12" font-weight="800" fill="{BG}" text-anchor="middle" letter-spacing="2">COMPLETE</text>
    <text x="{ox}" y="{oy + ph + 30}" font-size="12" fill="#2E9E52">&gt; portrait.svg loaded // terminal profile</text>

  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#39FF6A" stroke-opacity=".25"/>
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
