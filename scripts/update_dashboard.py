#!/usr/bin/env python3
"""Generate a robot-themed, data-driven GitHub profile dashboard using only Python stdlib."""
import datetime as dt
import html
import json
import os
import urllib.request
from collections import Counter
from pathlib import Path

USER = os.environ.get("GH_USERNAME", "Deepak-Kumar-Vishwakarma")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = Path("generated")
OUT.mkdir(exist_ok=True)

def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "profile-dashboard-generator",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))

def esc(value):
    return html.escape(str(value or ""), quote=True)

cache_path = OUT / "profile-data.json"
try:
    profile = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos?per_page=100&sort=updated&type=owner")
    repos = [r for r in repos if not r.get("fork") and not r.get("archived")]
    live_data = True
except Exception as error:
    # Keep the last successful snapshot visible during API outages or rate limits.
    print(f"GitHub API unavailable; using cached dashboard data: {error}")
    live_data = False
    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        cached = {}
    profile = {
        "public_repos": cached.get("public_repositories", 0),
        "followers": cached.get("followers", 0),
        "following": cached.get("following", 0),
    }
    repos = [{
        "name": r.get("name", "repository"),
        "description": r.get("description", ""),
        "language": r.get("language", ""),
        "stargazers_count": r.get("stars", 0),
        "forks_count": 0,
        "html_url": r.get("url", ""),
        "pushed_at": r.get("pushed_at", ""),
        "updated_at": r.get("pushed_at", ""),
        "fork": False,
        "archived": False,
    } for r in cached.get("recent_repositories", [])]
    if not repos:
        repos = []

events = []
if live_data:
    try:
        events = api(f"/users/{USER}/events/public?per_page=10")
    except Exception:
        pass

stars = sum(int(r.get("stargazers_count") or 0) for r in repos)
forks = sum(int(r.get("forks_count") or 0) for r in repos)
languages = Counter(r.get("language") for r in repos if r.get("language"))
top_languages = languages.most_common(5)
recent = sorted(repos, key=lambda r: r.get("pushed_at") or r.get("updated_at") or "", reverse=True)[:4]
if not live_data:
    stars = int(cached.get("stars_on_nonfork_repositories", stars))
    forks = int(cached.get("forks_on_nonfork_repositories", forks))
    top_languages = [(x.get("name", "Other"), int(x.get("repositories", 0))) for x in cached.get("top_languages", [])]
    if not recent:
        recent = [{**r, "stargazers_count": r.get("stars", 0), "html_url": r.get("url", f"https://github.com/{USER}/{r.get('name', '')}")} for r in cached.get("recent_repositories", [])]
now = dt.datetime.now(dt.timezone.utc)
updated = now.strftime("%d %b %Y · %H:%M UTC")

last_activity = "No recent public event"
if events:
    event = events[0]
    event_type = event.get("type", "Activity").replace("Event", "")
    repo_name = (event.get("repo") or {}).get("name", "")
    created = event.get("created_at", "")
    try:
        when = dt.datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%d %b · %H:%M UTC")
    except Exception:
        when = "Recently"
    last_activity = f"{event_type} · {repo_name} · {when}"

payload = {
    "username": USER,
    "generated_at": now.isoformat(),
    "public_repositories": profile.get("public_repos", len(repos)),
    "followers": profile.get("followers", 0),
    "following": profile.get("following", 0),
    "stars_on_nonfork_repositories": stars,
    "forks_on_nonfork_repositories": forks,
    "top_languages": [{"name": k, "repositories": v} for k, v in top_languages],
    "recent_repositories": [
        {"name": r["name"], "description": r.get("description") or "", "language": r.get("language") or "Other",
         "stars": r.get("stargazers_count", 0), "url": r.get("html_url", f"https://github.com/{USER}/{r['name']}"),
         "pushed_at": r.get("pushed_at") or r.get("updated_at")}
        for r in recent
    ],
    "latest_public_activity": last_activity,
    "data_source": "live GitHub API" if live_data else "cached last-known snapshot",
}
(OUT / "profile-data.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

language_text = "   /   ".join(f"{esc(k)}  {v}" for k, v in top_languages) or "Waiting for language data"
activity_text = esc(last_activity)
lang_svg = "   ·   ".join(f"{esc(k)} ({v})" for k, v in top_languages) or "No language data yet"

dashboard = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="540" viewBox="0 0 1200 540" role="img" aria-labelledby="title desc">
<title id="title">Deepak's live robot developer dashboard</title>
<desc id="desc">Animated futuristic robot with live GitHub repository, follower, star and language statistics. Generated {esc(updated)}.</desc>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#070B18"/><stop offset=".55" stop-color="#111638"/><stop offset="1" stop-color="#071C2B"/></linearGradient>
  <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#EAF8FF"/><stop offset=".28" stop-color="#718BAF"/><stop offset=".62" stop-color="#263C67"/><stop offset="1" stop-color="#101A35"/></linearGradient>
  <linearGradient id="cyan" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#79F7FF"/><stop offset="1" stop-color="#168CFF"/></linearGradient>
  <linearGradient id="violet" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#C2A0FF"/><stop offset="1" stop-color="#6A45E8"/></linearGradient>
  <radialGradient id="glow"><stop stop-color="#12D8FF" stop-opacity=".30"/><stop offset="1" stop-color="#12D8FF" stop-opacity="0"/></radialGradient>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#83B8FF" stroke-opacity=".10" stroke-width="1"/></pattern>
  <filter id="soft"><feGaussianBlur stdDeviation="12"/></filter>
  <filter id="neon"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <style>
    .label{{font:600 13px 'Segoe UI',Arial,sans-serif;letter-spacing:2px;fill:#88A5C8}}
    .value{{font:700 31px 'Segoe UI',Arial,sans-serif;fill:#F3F8FF}}
    .small{{font:500 14px 'Segoe UI',Arial,sans-serif;fill:#A9BEDA}}
    .tiny{{font:500 11px 'Segoe UI',Arial,sans-serif;fill:#7893B5;letter-spacing:1px}}
    .heading{{font:700 25px 'Segoe UI',Arial,sans-serif;fill:#F5FAFF;letter-spacing:1px}}
    .pulse{{animation:pulse 2.8s ease-in-out infinite}}
    .float{{animation:float 4.5s ease-in-out infinite}}
    .float2{{animation:float 5.5s ease-in-out infinite reverse}}
    .blink{{animation:blink 5s infinite}}
    .spin{{transform-origin:250px 270px;animation:spin 24s linear infinite}}
    @keyframes pulse{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}
    @keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-9px)}}}}
    @keyframes blink{{0%,44%,48%,100%{{opacity:1}}46%{{opacity:.08}}}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
  </style>
</defs>
<rect width="1200" height="540" rx="26" fill="url(#bg)"/>
<rect width="1200" height="540" rx="26" fill="url(#grid)"/>
<circle cx="255" cy="275" r="235" fill="url(#glow)"/>
<circle cx="255" cy="275" r="178" fill="none" stroke="#4CCEFF" stroke-opacity=".22" stroke-dasharray="3 11" class="spin"/>
<circle cx="255" cy="275" r="142" fill="none" stroke="#A98BFF" stroke-opacity=".35" stroke-dasharray="90 16 4 16" class="pulse"/>
<path d="M0 425 Q270 360 500 470 T1200 405" fill="none" stroke="#2C8FFF" stroke-opacity=".13" stroke-width="2"/>
<g class="float">
  <circle cx="95" cy="132" r="5" fill="#5CEBFF" filter="url(#neon)"/>
  <circle cx="415" cy="135" r="4" fill="#A88AFF"/>
  <circle cx="410" cy="390" r="6" fill="#5CEBFF" filter="url(#neon)"/>
  <path d="M100 350l7-13 7 13-7 13z" fill="#8E79FF" opacity=".7"/>
</g>
<!-- Friendly original robot illustration -->
<g transform="translate(80 72)">
  <path d="M175 90V63" stroke="#9AB6D9" stroke-width="9" stroke-linecap="round"/>
  <circle cx="175" cy="53" r="12" fill="url(#cyan)" filter="url(#neon)" class="pulse"/>
  <rect x="91" y="78" width="168" height="125" rx="38" fill="url(#metal)" stroke="#A5DFFF" stroke-width="3"/>
  <rect x="108" y="96" width="134" height="86" rx="26" fill="#07152C" stroke="#5BCFFF" stroke-opacity=".8" stroke-width="2"/>
  <g class="blink" filter="url(#neon)">
    <ellipse cx="145" cy="137" rx="12" ry="17" fill="#70F2FF"/>
    <ellipse cx="205" cy="137" rx="12" ry="17" fill="#70F2FF"/>
  </g>
  <path d="M151 160Q175 174 199 160" fill="none" stroke="#A78BFA" stroke-width="4" stroke-linecap="round"/>
  <path d="M87 118L65 130V163L91 169M263 118L285 130V163L259 169" fill="none" stroke="#8BA8CF" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="120" y="210" width="110" height="117" rx="28" fill="url(#metal)" stroke="#A5DFFF" stroke-width="3"/>
  <rect x="139" y="230" width="72" height="54" rx="14" fill="#07152C" stroke="#7D8CFF" stroke-width="2"/>
  <path d="M153 258h12l8-13 9 21 8-8h9" fill="none" stroke="#61F1FF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" filter="url(#neon)"/>
  <circle cx="175" cy="302" r="6" fill="#9B7BFF" class="pulse"/>
  <path d="M137 331v37m76-37v37" stroke="#A8C3E4" stroke-width="17" stroke-linecap="round"/>
  <path d="M119 370h35m43 0h35" stroke="#6DEBFF" stroke-width="8" stroke-linecap="round"/>
  <path d="M104 240l-28 25v48m169-73l28 25v48" fill="none" stroke="#8BA8CF" stroke-width="15" stroke-linecap="round"/>
  <circle cx="76" cy="316" r="13" fill="url(#violet)" stroke="#C8B6FF" stroke-width="2"/>
  <circle cx="274" cy="316" r="13" fill="url(#violet)" stroke="#C8B6FF" stroke-width="2"/>
  <path d="M130 80l-12-12m102 12l12-12" stroke="#B9D5F5" stroke-width="5" stroke-linecap="round"/>
</g>
<g transform="translate(485 55)">
  <text x="0" y="18" class="label">DEEPAK'S DEVELOPER SYSTEM</text>
  <text x="0" y="59" class="heading">ROBOT ASSISTANT ONLINE</text>
  <circle cx="8" cy="91" r="5" fill="#45F0B0" filter="url(#neon)"/>
  <text x="23" y="96" class="small">{"LIVE" if live_data else "CACHED FALLBACK"} GITHUB DATA  ·  REFRESHED EVERY 6 HOURS</text>
  <g transform="translate(0 130)">
    <rect width="205" height="91" rx="15" fill="#101E3B" stroke="#2B80B7" stroke-opacity=".8"/>
    <text x="18" y="28" class="label">PUBLIC REPOSITORIES</text>
    <text x="18" y="69" class="value">{int(profile.get("public_repos", len(repos)))}</text>
    <rect x="220" width="205" height="91" rx="15" fill="#101E3B" stroke="#765BCA" stroke-opacity=".8"/>
    <text x="238" y="28" class="label">TOTAL STARS</text>
    <text x="238" y="69" class="value">{stars}</text>
    <rect x="440" width="205" height="91" rx="15" fill="#101E3B" stroke="#2B80B7" stroke-opacity=".8"/>
    <text x="458" y="28" class="label">FOLLOWERS</text>
    <text x="458" y="69" class="value">{int(profile.get("followers", 0))}</text>
  </g>
  <g transform="translate(0 245)">
    <text x="0" y="0" class="label">LANGUAGE FOOTPRINT · REPOSITORY COUNTS</text>
    <text x="0" y="31" class="small">{lang_svg}</text>
    <path d="M0 54H645" stroke="#54759B" stroke-opacity=".35"/>
    <text x="0" y="86" class="label">LATEST PUBLIC ACTIVITY</text>
    <text x="0" y="111" class="small">{activity_text[:88]}</text>
  </g>
  <g transform="translate(0 430)">
    <text x="0" y="0" class="tiny">SYSTEM SNAPSHOT  ·  {esc(updated)}</text>
    <text x="645" y="0" text-anchor="end" class="tiny">POWERED BY GITHUB ACTIONS</text>
  </g>
</g>
<path d="M28 30h34M28 30v34M1172 30h-34M1172 30v34M28 510h34M28 510v-34M1172 510h-34M1172 510v-34" stroke="#63DFFF" stroke-opacity=".55" stroke-width="2" fill="none"/>
</svg>'''
(OUT / "robot-dashboard.svg").write_text(dashboard, encoding="utf-8")

cards = []
for i, r in enumerate(recent):
    x = 18 + i * 294
    name = esc(r.get("name", "Repository"))
    desc = esc(r.get("description") or "Open repository to explore the source code.")
    if len(desc) > 82:
        desc = desc[:79] + "..."
    lang = esc(r.get("language") or "Other")
    stars_count = int(r.get("stargazers_count") or 0)
    updated_at = (r.get("pushed_at") or r.get("updated_at") or "")[:10]
    url = esc(r.get("html_url") or f"https://github.com/{USER}/{r.get('name','')}")
    cards.append(f'''<a xlink:href="{url}" target="_blank">
<rect x="{x}" y="18" width="276" height="190" rx="16" fill="#101B34" stroke="#31577F"/>
<rect x="{x+18}" y="38" width="38" height="38" rx="10" fill="url(#icon)"/>
<path d="M{x+29} 57h16m-8-8v16" stroke="#E8F9FF" stroke-width="2" stroke-linecap="round"/>
<text x="{x+68}" y="53" class="name">{name[:34]}</text>
<text x="{x+68}" y="73" class="meta">{lang}  ·  ★ {stars_count}</text>
<text x="{x+18}" y="111" class="desc">{desc}</text>
<text x="{x+18}" y="177" class="meta">UPDATED  {esc(updated_at)}</text>
<path d="M{x+235} 174h20m-7-7 7 7-7 7" stroke="#68E8FF" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</a>''')

while len(cards) < 4:
    i = len(cards)
    x = 18 + i * 294
    cards.append(f'<rect x="{x}" y="18" width="276" height="190" rx="16" fill="#101B34" stroke="#31577F"/><text x="{x+18}" y="58" class="name">More projects coming</text><text x="{x+18}" y="92" class="desc">Explore all repositories on GitHub.</text>')

projects_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="230" viewBox="0 0 1200 230" role="img" aria-labelledby="t d">
<title id="t">Latest updated GitHub repositories</title><desc id="d">Automatically refreshed cards for the four most recently pushed non-fork repositories.</desc>
<defs><linearGradient id="icon"><stop stop-color="#7355D9"/><stop offset="1" stop-color="#118FB5"/></linearGradient>
<style>.name{{font:700 15px 'Segoe UI',Arial,sans-serif;fill:#F2F7FF}}.meta{{font:600 11px 'Segoe UI',Arial,sans-serif;fill:#77DDF2;letter-spacing:1px}}.desc{{font:13px 'Segoe UI',Arial,sans-serif;fill:#A9BCD5}}a:hover rect{{stroke:#65E7FF;stroke-width:2}}</style></defs>
<rect width="1200" height="230" rx="22" fill="#080F20"/>
{''.join(cards)}
</svg>'''
(OUT / "recent-projects.svg").write_text(projects_svg, encoding="utf-8")
print(f"Generated dashboard for {USER}: {len(repos)} non-fork repositories, {stars} stars.")
