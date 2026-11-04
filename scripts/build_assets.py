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


# ───────────────────────── hero / portrait ─────────────────────────
PORTRAIT_GREENS = ["#03140A", "#0A3D1C", "#13682F", "#1F9C45", "#33D461", "#8CFFAA"]


def portrait_paths(photo, ox, oy, cols, rows, px):
    from PIL import Image, ImageDraw, ImageFilter, ImageOps

    im = Image.open(photo).convert("L")
    # head + shoulders crop for the GitHub avatar (400x400 full-body shot)
    im = im.crop((122, 40, 262, 187))
    im = ImageOps.autocontrast(im, cutoff=2)
    # soft mask around head and torso so the busy background falls away
    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((34, 0, 104, 86), fill=255)       # head
    d.ellipse((4, 74, 136, 240), fill=255)      # shoulders / torso
    mask = mask.filter(ImageFilter.GaussianBlur(10))
    edges = im.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.6))
    small = im.resize((cols, rows), Image.LANCZOS)
    small_e = edges.resize((cols, rows), Image.LANCZOS)
    small_m = mask.resize((cols, rows), Image.LANCZOS)

    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    levels = len(PORTRAIT_GREENS) - 1
    paths = {i: [] for i in range(1, levels + 1)}
    for y in range(rows):
        run_lvl, run_start = 0, 0
        for x in range(cols + 1):
            if x < cols:
                v = small.getpixel((x, y)) / 255
                v = min(1.0, v * 0.85 + small_e.getpixel((x, y)) / 255 * 0.9)
                v *= 0.03 + 0.97 * small_m.getpixel((x, y)) / 255
                t = (bayer[y % 4][x % 4] + 0.5) / 16 - 0.5
                lvl = max(0, min(levels, int(v * levels + t + 0.5)))
            else:
                lvl = -1
            if lvl != run_lvl or x == cols:
                if run_lvl > 0:
                    paths[run_lvl].append(f"M{ox + run_start * px} {oy + y * px}h{(x - run_start) * px}v{px}h-{(x - run_start) * px}z")
                run_lvl, run_start = lvl, x
    return "".join(
        f'<path fill="{PORTRAIT_GREENS[l]}" d="{"".join(p)}"/>' for l, p in paths.items() if p
    )


def build_hero(photo):
    W, H = 1200, 440
    px, cols, rows = 4, 80, 84
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
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".28"/></pattern>
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

    <!-- right: portrait -->
    <rect x="{ox - 12}" y="{oy - 12}" width="{pw + 24}" height="{ph + 24}" fill="{PANEL}" stroke="#39FF6A" stroke-opacity=".35"/>
    <g clip-path="url(#pclip)">
      <rect x="{ox}" y="{oy}" width="{pw}" height="{ph}" fill="{PORTRAIT_GREENS[0]}"/>
      {portrait}
      <rect x="{ox}" y="{oy}" width="{pw}" height="{ph}" fill="url(#scan)"/>
      <rect class="beam" x="{ox}" y="{oy - 30}" width="{pw}" height="30" fill="#39FF6A" opacity=".12"/>
    </g>
    <rect x="{ox + pw - 96}" y="{oy - 24}" width="96" height="22" fill="#39FF6A"/>
    <text x="{ox + pw - 48}" y="{oy - 8}" font-size="12" font-weight="800" fill="{BG}" text-anchor="middle" letter-spacing="2">COMPLETE</text>
    <text x="{ox}" y="{oy + ph + 30}" font-size="12" fill="#2E9E52">&gt; portrait.svg loaded // terminal profile</text>

    <rect width="{W}" height="{H}" fill="url(#vig)"/>
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
