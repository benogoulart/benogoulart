#!/usr/bin/env python3
"""Generate metrics.svg — terminal-style GitHub profile card."""

import os
import sys
import json
import re
import subprocess
import textwrap
from pathlib import Path

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# ── paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "metrics.svg"

# ── colours ────────────────────────────────────────────────────────────
BG = "#11131A"
BG2 = "#151923"
FRAME = "#2A2F3A"
DIVIDER = "#262B35"
WHITE = "#D6D6D8"
MUTED = "#A9A9AE"
DARK = "#6E7078"
GREEN = "#73BF69"
BLUE = "#5B8CFF"
ORANGE = "#D9A15A"
RED = "#FF5F57"
YELLOW = "#FEBC2E"
GREEN_BTN = "#28C840"

# ── layout ─────────────────────────────────────────────────────────────
W = 860
H = 420
BAR_WIDTH = 200
BAR_TOTAL = 25  # chars inside [ ... ]

# ── font ───────────────────────────────────────────────────────────────
FONT = "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

# ── GitHub API ─────────────────────────────────────────────────────────
USERNAME = "benogoulart"
HEADERS = {"Accept": "application/vnd.github+json"}
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def gh(path: str):
    url = f"https://api.github.com{path}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_languages() -> list[tuple[str, float]]:
    """All languages by bytes across all repos, normalized to 100%."""
    repos = gh(f"/users/{USERNAME}/repos?per_page=100&sort=updated")
    lang_bytes: dict[str, int] = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        try:
            langs = gh(f"/repos/{USERNAME}/{repo['name']}/languages")
            for lang, b in langs.items():
                lang_bytes[lang] = lang_bytes.get(lang, 0) + b
        except Exception:
            continue
    total = sum(lang_bytes.values()) or 1
    ranked = sorted(lang_bytes.items(), key=lambda x: -x[1])
    return [(lang, round(b / total * 100, 2)) for lang, b in ranked]


def fetch_user_info() -> dict:
    return gh(f"/users/{USERNAME}")


def fetch_recent_activity() -> dict:
    events = gh(f"/users/{USERNAME}/events/public?per_page=100")
    commits = sum(1 for e in events if e["type"] == "PushEvent")
    prs_reviewed = sum(1 for e in events if e["type"] == "PullRequestReviewEvent")
    prs_opened = sum(1 for e in events if e["type"] == "PullRequestEvent" and e["payload"].get("action") == "opened")
    issues_opened = sum(1 for e in events if e["type"] == "IssuesEvent" and e["payload"].get("action") == "opened")
    issue_comments = sum(1 for e in events if e["type"] == "IssueCommentEvent")
    return {
        "commits": commits,
        "prs_reviewed": prs_reviewed,
        "prs_opened": prs_opened,
        "issues_opened": issues_opened,
        "issue_comments": issue_comments,
    }


def fetch_repos_count() -> int:
    repos = gh(f"/users/{USERNAME}/repos?per_page=100&sort=updated")
    return len([r for r in repos if not r.get("fork")])


def make_bar(pct: float) -> str:
    filled = round(pct / 100 * BAR_TOTAL)
    empty = BAR_TOTAL - filled
    return f"[{'#' * filled}{' ' * empty}]"


def build_svg(user: dict, langs: list, activity: dict, repos_count: int) -> str:
    created = user.get("created_at", "")[:10]
    followers = user.get("followers", 0)
    name = user.get("name") or USERNAME

    # calculate years since creation
    from datetime import datetime
    try:
        d = datetime.strptime(created, "%Y-%m-%d")
        years = (datetime.now() - d).days // 365
    except Exception:
        years = "?"

    def prompt_cmd(cmd: str) -> str:
        return (
            f'<tspan fill="{GREEN}">{USERNAME}</tspan>'
            f'<tspan fill="{MUTED}">@</tspan>'
            f'<tspan fill="{BLUE}">metrics</tspan>'
            f'<tspan fill="{MUTED}">:~# {cmd}</tspan>'
        )

    def anim(begin: float) -> str:
        return (
            f'<animate attributeName="opacity" from="0" to="1" begin="{begin:.2f}s" dur="0.4s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="0 5" to="0 0" begin="{begin:.2f}s" dur="0.4s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/>'
        )

    def line(y: int, begin: float, inner: str) -> str:
        return (
            f'<g opacity="0" transform="translate(0,5)">\n'
            f'<text x="20" y="{y}" fill="{WHITE}" font-size="14">{inner}</text>\n'
            f'{anim(begin)}\n'
            f'</g>'
        )

    def line_bold(y: int, begin: float, inner: str) -> str:
        return (
            f'<g opacity="0" transform="translate(0,5)">\n'
            f'<text x="20" y="{y}" font-size="14" font-weight="700">{inner}</text>\n'
            f'{anim(begin)}\n'
            f'</g>'
        )

    lines = []
    t = 0.15

    # ── whoami ──────────────────────────────────────────────────────
    lines.append(line_bold(55, t, prompt_cmd("whoami")))
    t += 0.10
    lines.append(line(78, t, f'<tspan fill="{GREEN}" font-weight="700">{name}</tspan> registered={years}y, uid={user.get("id", 0)}, gid=0'))
    t += 0.10
    lines.append(line(98, t, f'  contributed to <tspan fill="{GREEN}" font-weight="700">{repos_count}</tspan> repositories'))
    t += 0.10
    lines.append(line(118, t, f'  followed by <tspan fill="{GREEN}" font-weight="700">{followers}</tspan> users'))
    t += 0.10

    # ── git status ──────────────────────────────────────────────────
    lines.append(line_bold(148, t, prompt_cmd("git status")))
    t += 0.10
    lines.append(line_bold(171, t, f'<tspan fill="{BLUE}">Recent activity</tspan>'))
    t += 0.05
    lines.append(line(191, t, f'  <tspan fill="{GREEN}" font-weight="700">{activity["commits"]}</tspan> commits'))
    t += 0.05
    lines.append(line(211, t, f'  <tspan fill="{GREEN}" font-weight="700">{activity["prs_reviewed"]}</tspan> pull requests reviewed'))
    t += 0.05
    lines.append(line(231, t, f'  <tspan fill="{GREEN}" font-weight="700">{activity["prs_opened"]}</tspan> pull requests opened'))
    t += 0.05
    lines.append(line(251, t, f'  <tspan fill="{GREEN}" font-weight="700">{activity["issues_opened"]}</tspan> issues opened'))
    t += 0.05
    lines.append(line(271, t, f'  <tspan fill="{GREEN}" font-weight="700">{activity["issue_comments"]}</tspan> issue comments'))
    t += 0.10

    # ── locate (languages) ──────────────────────────────────────────
    lines.append(line_bold(301, t, prompt_cmd("locate")))
    t += 0.10
    y = 324
    for lang, pct in langs:
        bar = make_bar(pct)
        label = lang.upper()[:16].ljust(16)
        pct_str = f"{pct:.2f}%".rjust(6)
        lines.append(
            f'<g opacity="0" transform="translate(0,5)">\n'
            f'<text x="20" y="{y}" fill="{ORANGE}" font-size="14" font-weight="700">{label}</text>\n'
            f'<text x="155" y="{y}" fill="{WHITE}" font-size="14">{bar}</text>\n'
            f'<text x="375" y="{y}" fill="{MUTED}" font-size="14">{pct_str}</text>\n'
            f'{anim(t)}\n'
            f'</g>'
        )
        y += 20
        t += 0.05

    # ── footer ──────────────────────────────────────────────────────
    footer_y = y + 20
    lines.append(
        f'<g opacity="0" transform="translate(0,5)">\n'
        f'<text x="20" y="{footer_y}" fill="{MUTED}" font-size="12">Connection reset by 90.212.32.117</text>\n'
        f'{anim(t)}\n'
        f'</g>'
    )

    body = "\n".join(lines)
    total_h = footer_y + 26

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{total_h}" viewBox="0 0 {W} {total_h}" font-family="{FONT}">
<defs>
<linearGradient id="mbg" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{BG2}"/>
<stop offset="1" stop-color="{BG}"/>
</linearGradient>
</defs>
<rect width="{W}" height="{total_h}" rx="12" fill="url(#mbg)"/>
<rect x="0.5" y="0.5" width="{W - 1}" height="{total_h - 1}" rx="12" fill="none" stroke="{FRAME}"/>
<line x1="0" y1="30" x2="{W}" y2="30" stroke="{DIVIDER}"/>
<circle cx="20" cy="15" r="5" fill="{RED}"/>
<circle cx="36" cy="15" r="5" fill="{YELLOW}"/>
<circle cx="52" cy="15" r="5" fill="{GREEN_BTN}"/>
<text x="430" y="19" fill="{DARK}" font-size="12" text-anchor="middle">{USERNAME}@github: ~$ git log --oneline</text>
{body}
</svg>'''


def main():
    print("Fetching user info...")
    user = fetch_user_info()

    print("Fetching languages...")
    langs = fetch_languages()

    print("Fetching recent activity...")
    activity = fetch_recent_activity()

    print("Fetching repos count...")
    repos_count = fetch_repos_count()

    print("Building SVG...")
    svg = build_svg(user, langs, activity, repos_count)

    SVG.write_text(svg, encoding="utf-8")
    print(f"Written to {SVG}")


if __name__ == "__main__":
    main()
