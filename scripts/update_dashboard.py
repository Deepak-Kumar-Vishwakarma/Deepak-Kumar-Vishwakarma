#!/usr/bin/env python3
"""Build polished, data-backed SVGs for a GitHub profile README."""
import datetime as dt
import html
import json
import os
import textwrap
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

USER = os.environ.get("GH_USERNAME", "Deepak-Kumar-Vishwakarma")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = Path("generated")
OUT.mkdir(exist_ok=True)
CACHE = OUT / "profile-data.json"
PROFILE_REPO = USER.lower()

def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-profile-dashboard",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))

def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)

def short(value, limit):
    value = " ".join(str(value or "").split())
    if len(value) > limit:
        return value[:limit - 1].rstrip() + "…"
    return value

now = dt.datetime.now(dt.timezone.utc)
generated_at = now.isoformat()
display_time = now.strftime("%d %b %Y  /  %H:%M UTC")
live = True
try:
    profile = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos?per_page=100&sort=updated&type=owner")
    repos = [r for r in repos if not r.get("fork") and not r.get("archived") and r.get("name", "").lower() != PROFILE_REPO]
except Exception as exc:
    live = False
    print(f"GitHub API request failed; preserving last good snapshot: {exc}")
    try:
        cached = json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        cached = {}
    profile = {
        "public_repos": cached.get("public_repositories", 0),
        "followers": cached.get("followers", 0),
        "following": cached.get("following", 0),
    }
    repos = [{
        "name": r.get("name", "Repository"),
        "description": r.get("description", ""),
        "language": r.get("language", ""),
        "stargazers_count": r.get("stars", 0),
        "forks_count": 0,
        "html_url": r.get("url", f"https://github.com/{USER}/{r.get('name', '')}"),
        "pushed_at": r.get("pushed_at", ""),
        "updated_at": r.get("pushed_at", ""),
    } for r in cached.get("recent_repositories", [])]

if live:
    try:
        cached = json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        cached = {}

events = []
if live:
    try:
        events = api(f"/users/{USER}/events/public?per_page=30")
    except Exception as exc:
        print(f"Public events unavailable; continuing without activity: {exc}")

stars = sum(int(r.get("stargazers_count") or 0) for r in repos)
forks = sum(int(r.get("forks_count") or 0) for r in repos)
languages = Counter(r.get("language") for r in repos if r.get("language"))
top_languages = languages.most_common(5)
recent = sorted(repos, key=lambda r: r.get("pushed_at") or r.get("updated_at") or "", reverse=True)[:4]

activity = "No recent public activity outside this profile repository"
for event in events:
    repo_name = (event.get("repo") or {}).get("name", "")
    if repo_name.lower() == f"{USER}/{USER}".lower():
        continue
    event_type = event.get("type", "Activity").replace("Event", "")
    created = event.get("created_at", "")
    try:
        stamp = dt.datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%d %b %Y · %H:%M UTC")
    except Exception:
        stamp = "Recently"
    activity = f"{event_type} · {repo_name} · {stamp}"
    break

payload = {
    "username": USER,
    "generated_at": generated_at,
    "data_source": "live GitHub API" if live else "last successful cached snapshot",
    "public_repositories": int(profile.get("public_repos", 0)),
    "tracked_repositories": len(repos),
    "followers": int(profile.get("followers", 0)),
    "following": int(profile.get("following", 0)),
    "stars_on_nonfork_repositories": stars,
    "forks_on_nonfork_repositories": forks,
    "top_languages": [{"name": name, "repositories": count} for name, count in top_languages],
    "recent_repositories": [{
        "name": r.get("name", "Repository"),
        "description": r.get("description") or "",
        "language": r.get("language") or "Other",
        "stars": int(r.get("stargazers_count") or 0),
        "url": r.get("html_url") or f"https://github.com/{USER}/{r.get('name', '')}",
        "pushed_at": r.get("pushed_at") or r.get("updated_at") or "",
    } for r in recent],
    "latest_public_activity": activity,
}
CACHE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# High-contrast technical command console: no cartoon mascot or fabricated metrics.
language_rows = []
max_language = max([n for _, n in top_languages], default=1)
for index, (name, count) in enumerate(top_languages[:4]):
    y = 375 + index * 33
    bar_width = max(8, int(190 * count / max_language))
    language_rows.append(
        f'<text x="792" y="{y}" class="lang">{esc(name)}</text>'
        f'<rect x="930" y="{y-11}" width="190" height="7" rx="3.5" fill="#172943"/>'
        f'<rect x="930" y="{y-11}" width="{bar_width}" height="7" rx="3.5" fill="url(#cyan)"/>'
        f'<text x="1142" y="{y}" class="count" text-anchor="end">{count}</text>'
    )
if not language_rows:
    language_rows.append('<text x="792" y="375" class="muted">No language metadata available</text>')

status = "LIVE API" if live else "CACHED SNAPSHOT"
status_color = "#65F0BD" if live else "#FFC66D"
activity_text = short(activity, 62)
tracked = len(repos)

dashboard = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="590" viewBox="0 0 1440 590" role="img" aria-labelledby="title desc">
<title id="title">Deepak Kumar Vishwakarma — engineering and creative technology portfolio</title>
<desc id="desc">A work-focused portfolio dashboard featuring robotics and IoT, computer vision, game development, 3D creation, FDM printing and software tools, with live GitHub statistics.</desc>
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0B1118"/><stop offset=".55" stop-color="#121D23"/><stop offset="1" stop-color="#1B2529"/></linearGradient>
 <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#A5B8AE" stroke-opacity=".055"/></pattern>
 <style>
 .eyebrow{{font:600 11px 'Segoe UI',Arial,sans-serif;letter-spacing:2.5px;fill:#8EA69B}}
 .hero{{font:700 34px 'Segoe UI',Arial,sans-serif;fill:#F1F5F0}}
 .sub{{font:400 14px 'Segoe UI',Arial,sans-serif;fill:#AABBB2}}
 .label{{font:600 10px 'Segoe UI',Arial,sans-serif;letter-spacing:1.5px;fill:#8EA49A}}
 .num{{font:700 27px 'Segoe UI',Arial,sans-serif;fill:#F2F5F0}}
 .note{{font:500 10px 'Segoe UI',Arial,sans-serif;fill:#81968C}}
 .section{{font:700 12px 'Segoe UI',Arial,sans-serif;letter-spacing:1.8px;fill:#D8E4DC}}
 .cardtitle{{font:700 16px 'Segoe UI',Arial,sans-serif;fill:#F0F4EF}}
 .copy{{font:400 12px 'Segoe UI',Arial,sans-serif;fill:#A6B6AD}}
 .tag{{font:600 9px 'Segoe UI',Arial,sans-serif;letter-spacing:1px;fill:#A2D7BB}}
 .lang{{font:600 11px 'Segoe UI',Arial,sans-serif;fill:#C6D5CC}}
 .pulse{{animation:pulse 3.6s ease-in-out infinite}}
 .trace{{stroke-dasharray:5 9;animation:trace 16s linear infinite}}
 @keyframes pulse{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}
 @keyframes trace{{to{{stroke-dashoffset:-140}}}}
 </style>
</defs>
<rect width="1440" height="590" rx="22" fill="url(#bg)"/><rect width="1440" height="590" rx="22" fill="url(#grid)"/>
<path d="M36 145H1404M36 552H1404" stroke="#3C5148" stroke-opacity=".7"/>
<text x="68" y="66" class="eyebrow">DEEPAK KUMAR VISHWAKARMA  /  ENGINEERING PORTFOLIO</text>
<text x="68" y="111" class="hero">Building things that move, think &amp; play.</text>
<text x="70" y="137" class="sub">Robotics · Embedded systems · Computer vision · Game development · 3D fabrication</text>
<rect x="1100" y="55" width="270" height="34" rx="17" fill="#183129" stroke="#426D5B"/>
<circle cx="1120" cy="72" r="4" fill="{status_color}" class="pulse"/>
<text x="1134" y="76" class="label" fill="{status_color}">{status}</text>
<text x="1370" y="112" text-anchor="end" class="note">{esc(display_time)}</text>
<!-- verified GitHub metrics -->
<g>
 <rect x="68" y="171" width="290" height="78" rx="9" fill="#172520" stroke="#3B594B"/>
 <text x="88" y="198" class="label">PUBLIC REPOSITORIES</text><text x="88" y="232" class="num">{int(profile.get("public_repos", 0))}</text>
 <rect x="378" y="171" width="290" height="78" rx="9" fill="#172520" stroke="#3B594B"/>
 <text x="398" y="198" class="label">PROJECT STARS</text><text x="398" y="232" class="num">{stars}</text>
 <rect x="688" y="171" width="290" height="78" rx="9" fill="#172520" stroke="#3B594B"/>
 <text x="708" y="198" class="label">FOLLOWERS</text><text x="708" y="232" class="num">{int(profile.get("followers", 0))}</text>
 <rect x="998" y="171" width="372" height="78" rx="9" fill="#172520" stroke="#3B594B"/>
 <text x="1018" y="198" class="label">TRACKED PROJECTS</text><text x="1018" y="232" class="num">{len(repos)}</text>
</g>
<text x="68" y="292" class="section">MY WORK  /  FOUR CONNECTED DISCIPLINES</text>
<path d="M68 305H1370" stroke="#648276" stroke-opacity=".55" class="trace"/>
<g>
 <rect x="68" y="326" width="310" height="180" rx="11" fill="#15251F" stroke="#476B57"/>
 <text x="90" y="357" class="eyebrow">01  /  HARDWARE + FIRMWARE</text>
 <text x="90" y="392" class="cardtitle">Robotics &amp; IoT</text>
 <text x="90" y="420" class="copy">ESP32 · Sensors · Blynk · Control</text>
 <text x="90" y="443" class="copy">Robo Vision · Robo Race · Telemetry</text>
 <rect x="90" y="465" width="162" height="22" rx="11" fill="#244336"/><text x="103" y="480" class="tag">CONNECTED SYSTEMS</text>
 <path d="M328 370h25v25h-25zm12-10v10m-12 12h-10m35 0h10m-23 13v10" stroke="#88C7A6" stroke-width="1.5" fill="none"/>
 <rect x="400" y="326" width="310" height="180" rx="11" fill="#211E2B" stroke="#62557D"/>
 <text x="422" y="357" class="eyebrow">02  /  REALTIME WORLDS</text>
 <text x="422" y="392" class="cardtitle">Games &amp; 3D Creation</text>
 <text x="422" y="420" class="copy">Unity · Unreal Engine · Blender</text>
 <text x="422" y="443" class="copy">Gameplay · Environments · Pixel art</text>
 <rect x="422" y="465" width="150" height="22" rx="11" fill="#382E4A"/><text x="435" y="480" class="tag">INTERACTIVE WORLDS</text>
 <path d="M670 370l19 11v22l-19 11-19-11v-22zM670 370v22m19-11-19 11-19-11m19 11v22" stroke="#B9A9E3" stroke-width="1.4" fill="none"/>
 <rect x="732" y="326" width="310" height="180" rx="11" fill="#252219" stroke="#74674C"/>
 <text x="754" y="357" class="eyebrow">03  /  PROTOTYPING</text>
 <text x="754" y="392" class="cardtitle">3D Printing &amp; Making</text>
 <text x="754" y="420" class="copy">FDM · Motion systems · Calibration</text>
 <text x="754" y="443" class="copy">CAD workflows · Physical prototypes</text>
 <rect x="754" y="465" width="150" height="22" rx="11" fill="#403824"/><text x="767" y="480" class="tag">DIGITAL TO PHYSICAL</text>
 <path d="M1000 371h23v5h-23zm3 5v34m17-34v34m-26 0h32m-23-24h14m-14 10h14" stroke="#D8BE87" stroke-width="1.5" fill="none"/>
 <rect x="1064" y="326" width="306" height="180" rx="11" fill="#18252A" stroke="#496571"/>
 <text x="1086" y="357" class="eyebrow">04  /  SOFTWARE TOOLING</text>
 <text x="1086" y="392" class="cardtitle">Code &amp; Automation</text>
 <text x="1086" y="420" class="copy">Python · C/C++ · Java · Web</text>
 <text x="1086" y="443" class="copy">Aseprite builds · Developer tools</text>
 <rect x="1086" y="465" width="142" height="22" rx="11" fill="#263D45"/><text x="1099" y="480" class="tag">TOOLS THAT SHIP</text>
 <path d="M1330 371h-22v14h22v14h-22v14h22m-7-56v-7m-8 70v7" stroke="#90C5D2" stroke-width="1.5" fill="none"/>
</g>
<text x="68" y="548" class="label">LANGUAGES IN PUBLIC REPOSITORIES</text>
{''.join(language_lines)}
<text x="1370" y="548" text-anchor="end" class="note">AUTOMATIC REFRESH  /  6 HOURS</text>
</svg>'''
(OUT / "robot-dashboard.svg").write_text(dashboard, encoding="utf-8")

# Compact repository tiles with safe text lengths and real metadata only.
cards = []
for i, r in enumerate(recent):
    x = 24 + i * 350
    name = esc(short(r.get("name"), 29))
    description = r.get("description") or (f"{r.get('language') or 'Software'} repository" if r.get("language") else "Open the repository to inspect the project")
    description = esc(short(description, 49))
    language = esc(short(r.get("language") or "Unclassified", 16))
    stars_count = int(r.get("stargazers_count") or 0)
    pushed = r.get("pushed_at") or r.get("updated_at") or ""
    try:
        date = dt.datetime.fromisoformat(pushed.replace("Z", "+00:00")).strftime("%d %b %Y")
    except Exception:
        date = "Date unavailable"
    url = esc(r.get("html_url") or f"https://github.com/{USER}/{r.get('name', '')}")
    accent = "#55DCEB" if i % 2 == 0 else "#A58BFF"
    cards.append(f'''<a href="{url}" target="_blank">
<rect x="{x}" y="20" width="326" height="164" rx="13" fill="#0B172A" stroke="#294765"/>
<path d="M{x} 44V33Q{x} 20 {x+13} 20H{x+72}" fill="none" stroke="{accent}" stroke-width="2"/>
<text x="{x+20}" y="57" class="name">{name}</text>
<text x="{x+20}" y="88" class="desc">{description}</text>
<path d="M{x+20} 108H{x+306}" stroke="#29415C"/>
<text x="{x+20}" y="135" class="meta">{language}   /   ★ {stars_count}</text>
<text x="{x+20}" y="160" class="date">PUSHED  {esc(date)}</text>
<path d="M{x+285} 151h18m-7-7 7 7-7 7" stroke="{accent}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</a>''')
while len(cards) < 4:
    x = 24 + len(cards) * 350
    cards.append(f'<rect x="{x}" y="20" width="326" height="164" rx="13" fill="#0B172A" stroke="#294765"/><text x="{x+20}" y="57" class="name">More projects</text><text x="{x+20}" y="88" class="desc">Explore all repositories on GitHub.</text>')

projects_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="204" viewBox="0 0 1440 204" role="img" aria-labelledby="pt pd">
<title id="pt">Recently updated GitHub projects</title><desc id="pd">Four newest non-fork repositories, refreshed every six hours.</desc>
<defs><style>
.name{{font:700 15px 'Segoe UI',Arial,sans-serif;fill:#F0F7FF}}
.desc{{font:13px 'Segoe UI',Arial,sans-serif;fill:#A4B9D2}}
.meta{{font:600 11px 'Segoe UI',Arial,sans-serif;fill:#75DDF0;letter-spacing:1px}}
.date{{font:500 10px Consolas,monospace;fill:#6F8CAB;letter-spacing:.7px}}
a:hover rect{{stroke:#6CEAFF;stroke-width:2}}
</style></defs>
<rect width="1440" height="204" rx="18" fill="#060D1A"/>
{''.join(cards)}
</svg>'''
(OUT / "recent-projects.svg").write_text(projects_svg, encoding="utf-8")
print(f"Dashboard generated: live={live}, public_repositories={payload['public_repositories']}, tracked={tracked}, stars={stars}, followers={payload['followers']}.")
