"""Keep the bear in README.md true to Qi's last public push: the status line and the picture together.

    python3 tools/bear_status.py README.md                                # uses GITHUB_TOKEN if set
    python3 tools/bear_status.py README.md --now 2027-01-10T12:00:00Z     # see what a date would say

Rules: a push in the last 3 days is awake, in the last 2 weeks dozing, anything older hibernating.
Each state has its own picture, bear/<state>-light.png and -dark.png, made by `make`.
The time comes from each public repo's pushed_at rather than the events API, which on 2026-11-20 was
still missing pushes from the day before. The profile repo itself is left out, or the bot's own status
commits would keep the bear awake forever. Standard library only.
"""
import argparse
import datetime as dt
import json
import os
import re
import urllib.request
from zoneinfo import ZoneInfo

USER = "FuzzyLion"
HOME = ZoneInfo("Europe/Berlin")
BLOCKS = ("bear-picture", "bear-status")

ALT = {
    "awake": "A white plush bear in a grey scarf and a blue sweater, holding a steaming mug by a rainy window at night, drawn in black and white dots.",
    "dozing": "The same bear nodding off over its mug, eyes shut and mouth a little open, drawn in black and white dots.",
    "hibernating": "The same bear fast asleep, eyes shut, still holding its mug, drawn in black and white dots.",
}


def last_push():
    """The newest pushed_at among Qi's own public repos, leaving out forks and this profile repo."""
    request = urllib.request.Request(
        f"https://api.github.com/users/{USER}/repos?type=owner&sort=pushed&per_page=100",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "bear-status"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=20) as response:
        repos = json.load(response)
    times = [
        r["pushed_at"]
        for r in repos
        if r["pushed_at"] and not r["fork"] and not r["private"] and r["name"].lower() != USER.lower()
    ]
    return dt.datetime.fromisoformat(max(times).replace("Z", "+00:00")) if times else None


def status(pushed, now):
    """The state and the line that goes with it."""
    if pushed is None:
        return "hibernating", "Bear status: hibernating. No public repos to push to."
    when = pushed.astimezone(HOME)
    days = (now.astimezone(HOME).date() - when.date()).days
    date = f"{when.day} {when:%b}" + ("" if when.year == now.astimezone(HOME).year else f" {when.year}")
    if days < 3:
        return "awake", f"Bear status: awake. Last push on {date}."
    if days < 14:
        return "dozing", f"Bear status: dozing. Last push on {date}."
    line = f"Bear status: hibernating. Nothing pushed since {date}."
    return "hibernating", line + (" See you in spring." if now.astimezone(HOME).month in (11, 12, 1, 2, 3) else "")


def picture(state):
    # The <img> has to be a direct child of <picture>, or browsers ignore the dark <source> and the dark
    # theme gets the light picture (seen live on 2026-11-20). So the link goes around <picture>, inside a
    # <div> that keeps the whole thing one HTML block, the way Tailwind's and Next.js's READMEs do it.
    # The link is absolute because GitHub leaves relative hrefs here unrewritten, which 404 on the profile.
    # The width is a share of the README, not 320 px: on a ~400 px phone a fixed 320 px float left a
    # 60 px strip, and with GitHub's overflow-wrap: break-word the app stacked the title one letter per
    # line. 38% is about 320 px on desktop (846 px README) and about 150 px on a phone.
    return (
        "<div>\n"
        f'<a href="https://github.com/{USER}/{USER}/blob/main/bear/{state}.jpg">\n'
        "<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" srcset="bear/{state}-dark.png">\n'
        f'  <img align="right" width="38%" src="bear/{state}-light.png" alt="{ALT[state]}">\n'
        "</picture>\n"
        "</a>\n"
        "</div>"
    )


def replace(text, name, body):
    start, end = f"<!-- {name} -->", f"<!-- /{name} -->"
    block = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not block.search(text):
        raise SystemExit(f"README has no {start} ... {end} block")
    return block.sub(lambda _: f"{start}\n{body}\n{end}", text, count=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("readme")
    parser.add_argument("--now", help="ISO time to judge against, for trying it out")
    args = parser.parse_args()

    now = dt.datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else dt.datetime.now(dt.timezone.utc)
    state, line = status(last_push(), now)

    text = open(args.readme, encoding="utf-8").read()
    new = replace(replace(text, "bear-picture", picture(state)), "bear-status", line)
    if new != text:
        open(args.readme, "w", encoding="utf-8").write(new)
    print(("updated: " if new != text else "unchanged: ") + line)


if __name__ == "__main__":
    main()
