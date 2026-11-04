"""Generates the animated hero card and the top-languages card as local SVG files.

No external image services are used. Live numbers come from the GitHub GraphQL API.
Without a token (or on API errors) the hero still renders with placeholder dashes.
"""
import html
import json
import os
import urllib.request

LOGIN = os.environ.get("GH_LOGIN", "YunisPashayev")
TOKEN = os.environ.get("GH_TOKEN", "")
HERE = os.path.dirname(os.path.abspath(__file__))

# ---- palette -------------------------------------------------------------
BG, PANEL, BORDER = "#0D111B", "#10161D", "#22475A"
CYAN, VIOLET, BLUE = "#2BC4F5", "#8B5CF6", "#3B82F6"
TEXT, MUTED, LINE = "#C9D1D9", "#64748B", "#2A3B55"
PALETTE = ["#2BC4F5", "#3B82F6", "#8B5CF6", "#A78BFA", "#22D3EE", "#60A5FA"]
RAMP = " .'`,:;-~=+*ixoXO#%@"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono','DejaVu Sans Mono',monospace"
SANS = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"

PHRASES = [
    "Java Backend Developer",
    "Spring Boot • Microservices",
    "Kafka • RabbitMQ • Redis",
    "REST APIs • Security • AWS",
]

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, after: $cursor) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


def gql(variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["user"]


def fetch():
    """Returns ({'stars','commits','repos','followers'}, {language: bytes})."""
    stars = repos = 0
    langs, cursor, first = {}, None, None
    while True:
        user = gql({"login": LOGIN, "cursor": cursor})
        first = first or user
        page = user["repositories"]
        for repo in page["nodes"]:
            repos += 1
            stars += repo["stargazerCount"]
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                langs[name] = langs.get(name, 0) + edge["size"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    cc = first["contributionsCollection"]
    stats = {
        "stars": stars,
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "repos": repos,
        "followers": first["followers"]["totalCount"],
    }
    return stats, langs


# ---- helpers --------------------------------------------------------------
def lerp_color(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(pa, pb))


def fmt(n):
    if n is None:
        return "—"
    return f"{n / 1000:.1f}K".replace(".0K", "K") if n >= 10000 else f"{n:,}"


# ---- top languages card ---------------------------------------------------
def card(title, body, height=195):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="{height}" viewBox="0 0 420 {height}">
  <style>
    text {{ font-family: 'Segoe UI', Ubuntu, Arial, sans-serif; }}
    .t {{ font-size: 18px; font-weight: 600; fill: {CYAN}; }}
    .l {{ font-size: 14px; fill: {TEXT}; }}
    .v {{ font-size: 14px; font-weight: 700; fill: #A78BFA; }}
  </style>
  <rect x="0.5" y="0.5" width="419" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
  <text x="25" y="35" class="t">{html.escape(title)}</text>
  {body}
</svg>
"""


def langs_svg(langs):
    top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6]
    total = sum(size for _, size in top) or 1
    x, segments, legend = 25.0, [], []
    for i, (name, size) in enumerate(top):
        color = PALETTE[i % len(PALETTE)]
        width = 370 * size / total
        segments.append(f'<rect x="{x:.2f}" y="55" width="{width:.2f}" height="10" fill="{color}"/>')
        x += width
        lx, ly = 25 + (i % 2) * 190, 98 + (i // 2) * 30
        legend.append(
            f'<circle cx="{lx + 5}" cy="{ly - 5}" r="5" fill="{color}"/>'
            f'<text x="{lx + 18}" y="{ly}" class="l">{html.escape(name)}</text>'
            f'<text x="{lx + 165}" y="{ly}" class="v" text-anchor="end">{100 * size / total:.1f}%</text>'
        )
    body = (
        '<clipPath id="bar"><rect x="25" y="55" width="370" height="10" rx="5"/></clipPath>'
        f'<g clip-path="url(#bar)">{"".join(segments)}</g>\n  ' + "\n  ".join(legend)
    )
    return card("Most Used Languages", body)


# ---- hero card ------------------------------------------------------------
def portrait_svg(lines, x0=26, y0=84, cw=5.9, lh=11.2):
    nb, n, out = 6, len(RAMP), []
    for r, line in enumerate(lines):
        stripped = line.rstrip()
        if not stripped.strip():
            continue
        first, last = len(line) - len(line.lstrip()), len(stripped) - 1
        runs, cur, buf = [], 0, ""
        for c in range(first, last + 1):
            ch = line[c]
            b = cur if ch == " " else round(RAMP.index(ch) / (n - 1) * (nb - 1)) if ch in RAMP else cur
            if b != cur and buf:
                runs.append((cur, buf))
                buf = ""
            cur = b
            buf += ch
        runs.append((cur, buf))
        spans = "".join(f'<tspan class="c{b}">{html.escape(t)}</tspan>' for b, t in runs)
        out.append(
            f'<text x="{x0 + first * cw:.1f}" y="{y0 + r * lh:.1f}" '
            f'textLength="{(last - first + 1) * cw:.1f}" lengthAdjust="spacing" xml:space="preserve">{spans}</text>'
        )
    return "\n".join(out)


def typing_svg(x, y, size=20, per=4.6):
    """Self-contained typing/erasing animation (pure CSS, works inside <img>)."""
    cw = size * 0.6
    total = per * len(PHRASES)
    css, body = [], []
    for i, phrase in enumerate(PHRASES):
        n = len(phrase)
        w = n * cw
        s = i * per / total * 100
        a = s + 0.001
        b = s + per * 0.30 / total * 100          # typed
        c = s + per * 0.78 / total * 100          # held
        d = s + per * 0.92 / total * 100          # erased
        e = (i + 1) * per / total * 100
        steps = f"animation-timing-function:steps({n},end)"
        css.append(
            f"@keyframes w{i}{{0%{{width:0}}{a:.3f}%{{width:0;{steps}}}{b:.3f}%{{width:{w:.1f}px}}"
            f"{c:.3f}%{{width:{w:.1f}px;{steps}}}{d:.3f}%{{width:0}}100%{{width:0}}}}"
            f"@keyframes k{i}{{0%{{transform:translateX(0);opacity:0}}{(f'{s:.3f}%{{opacity:0}}' if s > 0 else '')}{a:.3f}%{{transform:translateX(0);opacity:1;{steps}}}"
            f"{b:.3f}%{{transform:translateX({w:.1f}px);opacity:1}}{c:.3f}%{{transform:translateX({w:.1f}px);opacity:1;{steps}}}"
            f"{d:.3f}%{{transform:translateX(0);opacity:1}}{min(d + 0.01, 100):.3f}%{{transform:translateX(0);opacity:0}}100%{{opacity:0}}}}"
            f".w{i}{{animation:w{i} {total}s linear infinite}}.k{i}{{animation:k{i} {total}s linear infinite}}"
        )
        body.append(
            f'<clipPath id="cp{i}"><rect class="w{i}" x="{x}" y="{y - size}" width="0" height="{size * 1.5:.0f}"/></clipPath>'
            f'<text x="{x}" y="{y}" class="typ" clip-path="url(#cp{i})" textLength="{w:.1f}" lengthAdjust="spacing" xml:space="preserve">{html.escape(phrase)}</text>'
            f'<rect class="k{i}" x="{x}" y="{y - size + 2}" width="2.4" height="{size:.0f}" rx="1" fill="{CYAN}" opacity="0"/>'
        )
    return "\n".join(css), "\n".join(body)


def tile(x, y, w, h, label, value):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#0A0F18" stroke="{BORDER}"/>'
        f'<text x="{x + 18}" y="{y + 26}" class="tl">{html.escape(label)}</text>'
        f'<text x="{x + 18}" y="{y + 64}" class="tv">{html.escape(fmt(value))}</text>'
        f'<rect x="{x + 18}" y="{y + h - 16}" width="{w - 36}" height="4" rx="2" fill="url(#bar)" opacity="0.85"/>'
    )


def hero_svg(stats, art):
    W, H = 960, 560
    IL, IR = 486, 934
    nb = 6
    css_levels = "\n".join(
        f".c{i}{{fill:{lerp_color(VIOLET, CYAN, 0.22 + 0.78 * (i / (nb - 1)) ** 0.8)}}}" for i in range(nb)
    )
    typ_css, typ_body = typing_svg(IL, 168)
    tw = (IR - IL - 14) / 2
    tiles = "".join([
        tile(IL, 226, tw, 96, "STARS", stats.get("stars")),
        tile(IL + tw + 14, 226, tw, 96, "COMMITS · LAST YEAR", stats.get("commits")),
        tile(IL, 336, tw, 96, "REPOS", stats.get("repos")),
        tile(IL + tw + 14, 336, tw, 96, "FOLLOWERS", stats.get("followers")),
    ])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(LOGIN)} - Java Backend Developer">
<style>
text{{font-family:{FONT}}}
.art text{{font-size:9.8px}}
{css_levels}
.file{{font-size:13px;fill:{TEXT};font-family:{SANS}}}
.head{{font-size:14px;font-weight:700;fill:{CYAN}}}
.dim{{font-size:13px;fill:{MUTED}}}
.typ{{font-size:20px;font-weight:700;fill:url(#tg)}}
.tl{{font-size:11px;letter-spacing:2.2px;font-weight:700;fill:#7DD3FC;font-family:{SANS}}}
.tv{{font-size:34px;font-weight:800;fill:url(#tg);font-family:{SANS}}}
.ok{{font-size:13px;fill:#7DD3FC}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.25}}}}
.pulse{{animation:pulse 2s ease-in-out infinite}}
@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
.blink{{animation:blink 1.1s steps(1) infinite}}
{typ_css}
</style>
<defs>
  <linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CYAN}"/><stop offset="0.55" stop-color="{BORDER}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>
  <linearGradient id="tg" gradientUnits="userSpaceOnUse" x1="{IL}" y1="0" x2="{IR}" y2="0"><stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="#A78BFA"/></linearGradient>
  <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>
  <radialGradient id="glow" cx="0.28" cy="0.55" r="0.5"><stop offset="0" stop-color="{CYAN}" stop-opacity="0.13"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
  <clipPath id="card"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14"/></clipPath>
</defs>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{BG}"/>
<g clip-path="url(#card)">
  <rect x="1" y="1" width="{W - 2}" height="46" fill="{PANEL}"/>
  <rect x="0" y="47" width="{W}" height="{H - 47}" fill="url(#glow)"/>
</g>
<line x1="1" y1="47" x2="{W - 1}" y2="47" stroke="{BORDER}"/>
<circle cx="28" cy="24" r="6" fill="#FF5F57"/><circle cx="48" cy="24" r="6" fill="#FEBC2E"/><circle cx="68" cy="24" r="6" fill="#28C840"/>
<text x="90" y="29" class="file">{html.escape(LOGIN)} / README.md</text>
<g class="art">
{art}
</g>
<text x="{IL}" y="92" class="head">github@{html.escape(LOGIN)}</text>
<line x1="{IL + (len(LOGIN) + 7) * 8.4 + 8:.1f}" y1="88" x2="{IR}" y2="88" stroke="{LINE}" stroke-width="1.4"/>
<text x="{IL}" y="130" class="dim">$ whoami</text>
{typ_body}
<text x="{IL}" y="206" class="dim">$ ./profile --signal</text>
{tiles}
<circle class="pulse" cx="{IL + 5}" cy="466" r="4.5" fill="{CYAN}"/>
<text x="{IL + 18}" y="470" class="ok">status: running (stable)</text>
<text x="{IL}" y="508" class="dim">// Clean code. Reliable systems.</text>
<text x="{IL + 33 * 7.8 + 6:.1f}" y="508" class="dim blink">▌</text>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="none" stroke="url(#bd)" stroke-width="1.5"/>
</svg>
"""


def main():
    stats, langs = {}, {}
    if TOKEN:
        try:
            stats, langs = fetch()
        except Exception as exc:  # keep previous cards if the API fails
            print("API error, using placeholders:", exc)
    with open(os.path.join(HERE, "portrait.txt"), encoding="utf-8") as f:
        rows = f.read().replace("\r", "").split("\n")
    if rows and rows[0].startswith("# portrait"):  # header protects the first row from editor trimming
        rows = rows[1:]
    art = portrait_svg(rows)
    os.makedirs("assets", exist_ok=True)
    with open("assets/hero.svg", "w", encoding="utf-8") as f:
        f.write(hero_svg(stats, art))
    if langs:
        with open("assets/top-langs.svg", "w", encoding="utf-8") as f:
            f.write(langs_svg(langs))
    print("Generated:", stats, sorted(langs.items(), key=lambda kv: -kv[1])[:6])


if __name__ == "__main__":
    main()
