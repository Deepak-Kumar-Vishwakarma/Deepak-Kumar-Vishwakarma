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

dashboard = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="620" viewBox="0 0 1440 620" role="img" aria-labelledby="title desc">
<title id="title">Deepak Kumar Vishwakarma — robotics developer command center</title>
<desc id="desc">A premium dark sci-fi telemetry dashboard with animated radar, repository statistics, language distribution and public activity. Snapshot {esc(display_time)}.</desc>
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#050914"/><stop offset=".52" stop-color="#0A1428"/><stop offset="1" stop-color="#10102A"/></linearGradient>
 <linearGradient id="panel" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#101E35" stop-opacity=".96"/><stop offset="1" stop-color="#091426" stop-opacity=".96"/></linearGradient>
 <linearGradient id="cyan" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#31D9E9"/><stop offset="1" stop-color="#4C8DFF"/></linearGradient>
 <linearGradient id="violet" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#B68BFF"/><stop offset="1" stop-color="#6856E8"/></linearGradient>
 <radialGradient id="core"><stop stop-color="#65EFFF" stop-opacity=".35"/><stop offset=".5" stop-color="#3277FF" stop-opacity=".10"/><stop offset="1" stop-color="#3277FF" stop-opacity="0"/></radialGradient>
 <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M28 0H0V28" fill="none" stroke="#7DA8D8" stroke-opacity=".075" stroke-width="1"/></pattern>
 <filter id="glow"><feGaussianBlur stdDeviation="7" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
 <clipPath id="screen"><rect x="34" y="34" width="1372" height="552" rx="18"/></clipPath>
 <style>
 .eyebrow{{font:600 12px 'Segoe UI',Arial,sans-serif;letter-spacing:3px;fill:#7797BA}}
 .title{{font:700 30px 'Segoe UI',Arial,sans-serif;letter-spacing:1.2px;fill:#F0F7FF}}
 .sub{{font:500 14px 'Segoe UI',Arial,sans-serif;fill:#9DB4D0}}
 .metric-label{{font:600 11px 'Segoe UI',Arial,sans-serif;letter-spacing:1.8px;fill:#819AB8}}
 .metric{{font:700 34px 'Segoe UI',Arial,sans-serif;fill:#F5FAFF}}
 .metric-foot{{font:500 11px 'Segoe UI',Arial,sans-serif;fill:#6886A7}}
 .section{{font:700 13px 'Segoe UI',Arial,sans-serif;letter-spacing:2px;fill:#BBD1E8}}
 .lang{{font:600 12px 'Segoe UI',Arial,sans-serif;fill:#C8D9EB}}
 .count{{font:600 11px 'Segoe UI',Arial,sans-serif;fill:#82DDF4}}
 .muted{{font:500 12px 'Segoe UI',Arial,sans-serif;fill:#819AB8}}
 .mono{{font:500 11px Consolas,monospace;fill:#7898B9;letter-spacing:.5px}}
 .orbit{{transform-origin:330px 324px;animation:orbit 28s linear infinite}}
 .scan{{animation:scan 5s ease-in-out infinite}}
 .corepulse{{animation:corepulse 3s ease-in-out infinite}}
 .dash{{stroke-dasharray:5 12;animation:dash 18s linear infinite}}
 @keyframes orbit{{to{{transform:rotate(360deg)}}}}
 @keyframes scan{{0%,100%{{opacity:.2;transform:translateY(-90px)}}50%{{opacity:.85;transform:translateY(90px)}}}}
 @keyframes corepulse{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}
 @keyframes dash{{to{{stroke-dashoffset:-180}}}}
 </style>
</defs>
<rect width="1440" height="620" rx="26" fill="url(#bg)"/>
<g clip-path="url(#screen)">
 <rect x="34" y="34" width="1372" height="552" fill="url(#grid)"/>
 <path d="M34 132H1406M34 566H1406" stroke="#294461" stroke-opacity=".6"/>
 <path d="M34 34H1406V586H34Z" fill="none" stroke="#294765" stroke-width="1.2"/>
 <!-- left telemetry / sensor core -->
 <circle cx="330" cy="324" r="235" fill="url(#core)"/>
 <circle cx="330" cy="324" r="190" fill="none" stroke="#3C759E" stroke-opacity=".22" stroke-width="1"/>
 <circle cx="330" cy="324" r="166" fill="none" stroke="#57D9F3" stroke-opacity=".28" stroke-dasharray="2 9"/>
 <circle cx="330" cy="324" r="132" fill="none" stroke="#7785FF" stroke-opacity=".42" stroke-dasharray="84 12 3 12" class="orbit"/>
 <circle cx="330" cy="324" r="100" fill="none" stroke="#3CCCEB" stroke-opacity=".28"/>
 <circle cx="330" cy="324" r="74" fill="#0C1B31" stroke="#59D8F2" stroke-opacity=".6" stroke-width="1.5"/>
 <circle cx="330" cy="324" r="57" fill="url(#core)" class="corepulse"/>
 <path d="M330 153V495M159 324H501M209 203L451 445M451 203L209 445" stroke="#3E729A" stroke-opacity=".18"/>
 <g class="orbit"><path d="M330 127l-7 16h14z" fill="#64E8FF" filter="url(#glow)"/><circle cx="330" cy="134" r="4" fill="#D5FBFF"/></g>
 <g filter="url(#glow)" class="corepulse">
  <path d="M284 324h25l13-24 18 49 14-25h22" fill="none" stroke="#72E9FF" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="330" cy="324" r="7" fill="#DDFBFF"/>
 </g>
 <path d="M145 324A185 185 0 0 1 515 324" fill="none" stroke="#5DE6FF" stroke-opacity=".28" stroke-width="2" class="dash"/>
 <path d="M145 324A185 185 0 0 0 515 324" fill="none" stroke="#A28BFF" stroke-opacity=".2" stroke-width="2"/>
 <rect x="145" y="245" width="370" height="158" fill="url(#cyan)" opacity=".025" class="scan"/>
 <text x="330" y="540" text-anchor="middle" class="mono">SENSOR ARRAY  /  TELEMETRY ACTIVE</text>
 <!-- top heading -->
 <text x="82" y="80" class="eyebrow">DKV  /  ENGINEERING PROFILE SYSTEM</text>
 <text x="82" y="115" class="title">ROBOTICS &amp; SOFTWARE LAB</text>
 <text x="1360" y="82" text-anchor="end" class="eyebrow">SYSTEM STATUS</text>
 <circle cx="1198" cy="108" r="4" fill="{status_color}" filter="url(#glow)"/>
 <text x="1212" y="113" class="section" fill="{status_color}">{status}</text>
 <text x="1360" y="137" text-anchor="end" class="mono">UPDATED  {esc(display_time)}</text>
 <!-- right data modules -->
 <g>
  <rect x="590" y="166" width="235" height="128" rx="12" fill="url(#panel)" stroke="#284A68"/>
  <path d="M590 179V166H603M812 166H825V179" stroke="#55D9EF" stroke-width="2" fill="none"/>
  <text x="612" y="198" class="metric-label">PUBLIC REPOSITORIES</text>
  <text x="612" y="247" class="metric">{int(profile.get("public_repos", 0))}</text>
  <text x="612" y="273" class="metric-foot">{tracked} TRACKED NON-FORK PROJECTS</text>
  <rect x="842" y="166" width="235" height="128" rx="12" fill="url(#panel)" stroke="#3A3D72"/>
  <path d="M842 179V166H855M1064 166H1077V179" stroke="#A58BFF" stroke-width="2" fill="none"/>
  <text x="864" y="198" class="metric-label">TOTAL STARS</text>
  <text x="864" y="247" class="metric">{stars}</text>
  <text x="864" y="273" class="metric-foot">ON OWN NON-FORK PROJECTS</text>
  <rect x="1094" y="166" width="270" height="128" rx="12" fill="url(#panel)" stroke="#284A68"/>
  <path d="M1094 179V166H1107M1351 166H1364V179" stroke="#55D9EF" stroke-width="2" fill="none"/>
  <text x="1116" y="198" class="metric-label">FOLLOWERS</text>
  <text x="1116" y="247" class="metric">{int(profile.get("followers", 0))}</text>
  <text x="1116" y="273" class="metric-foot">FOLLOWING  {int(profile.get("following", 0))}</text>
 </g>
 <path d="M590 324H1364" stroke="#294765" stroke-opacity=".8"/>
 <text x="590" y="355" class="section">LANGUAGE DISTRIBUTION</text>
 {''.join(language_rows)}
 <path d="M1170 342V475" stroke="#294765"/>
 <text x="1200" y="355" class="section">REPOSITORY FORKS</text>
 <text x="1200" y="398" class="metric">{forks}</text>
 <text x="1200" y="422" class="metric-foot">OWN PROJECT FORKS</text>
 <text x="590" y="520" class="section">LATEST PUBLIC ACTIVITY</text>
 <text x="590" y="545" class="sub">{esc(activity_text)}</text>
 <text x="1360" y="545" text-anchor="end" class="mono">REFRESH CYCLE  /  06H</text>
</g>
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
