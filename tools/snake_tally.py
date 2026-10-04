#!/usr/bin/env python3
"""
Replace snk's progress bar with a commit tally.

snk draws a bar under the snake that grows by one step per square eaten,
whatever the square's count. This swaps it for a bar that grows by each
eaten day's share of the year's contributions, with a counter beside it
("23 / 76 contributions") that ticks up in step with the snake.

    GITHUB_TOKEN=... python3 tools/snake_tally.py USER SVG THEME [SVG THEME ...]

THEME is dark or light. If an SVG doesn't look the way this expects (snk
changed its output), the bar is removed instead, so nothing broken ships.
Standard library only.
"""

import datetime as dt
import json
import os
import re
import sys
import urllib.request

TEXT = {"dark": "#8b949e", "light": "#57606a"}
TRACK = {"dark": "#21262d", "light": "#eaeef2"}
BAR_W = 620


def calendar(user, token):
    q = ('{ user(login: "%s") { contributionsCollection { contributionCalendar '
         '{ totalContributions weeks { contributionDays { weekday contributionCount } } } } } }' % user)
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=json.dumps({"query": q}).encode(),
        headers={"Authorization": "bearer " + token, "Content-Type": "application/json",
                 "User-Agent": "snake-tally"})
    with urllib.request.urlopen(req, timeout=30) as r:
        cal = json.loads(r.read())["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    grid = {}
    for col, w in enumerate(cal["weeks"]):
        for d in w["contributionDays"]:
            grid[(col, d["weekday"])] = d["contributionCount"]
    return grid, cal["totalContributions"]


def strip_bar(svg):
    svg = re.sub(r'<rect class="u u\d+"[^>]*/>', "", svg)
    return re.sub(r'(@keyframes u\d+\{(?:[^{}]*\{[^}]*\})*\}\.u\.u\d+\{[^}]*\})|(\.u\{[^}]*\})', "", svg)


def tally(svg, grid, total, theme):
    dur = re.search(r'animation:none (\d+)ms linear infinite', svg)
    bar = re.search(r'<rect class="u u0"[^>]*y="([\d.]+)"', svg)
    if not dur or not bar or not total:
        raise ValueError("unexpected snk output")
    y = float(bar.group(1))
    cells = []   # (time %, col, row) for every square the snake eats
    for cls, x, yy in re.findall(r'<rect class="c (c[0-9a-z]+)" x="([\d.]+)" y="([\d.]+)"', svg):
        kf = re.search(r'@keyframes %s\{([\d.]+)%%' % re.escape(cls), svg)
        if not kf:
            raise ValueError("no timing for " + cls)
        cells.append((float(kf.group(1)), round((float(x) - 2) / 16), round((float(yy) - 2) / 16)))
    # snk and the calendar can disagree by a week column at the edges (time
    # zones, a new week starting between the two). Use the shift under which
    # the most eaten squares land on days that have contributions.
    off = max(range(-2, 3), key=lambda o: (sum(1 for _, c, r in cells if grid.get((c + o, r), 0)), -abs(o)))
    eaten = [(t, grid.get((c + off, r), 0)) for t, c, r in cells]
    if not eaten:
        raise ValueError("no cells")
    eaten.sort()

    steps, run = [], 0
    for t, n in eaten:
        run += n
        steps.append((t, run))

    # Bar: jumps to cumulative/total at each eat time.
    kf = ["0%%,%.2f%%{transform:scale(0,1)}" % steps[0][0]]
    for i, (t, s) in enumerate(steps):
        end = steps[i + 1][0] if i + 1 < len(steps) else 100
        kf.append("%.2f%%,%.2f%%{transform:scale(%.4f,1)}" % (t + 0.02, end, s / total))
    css = (".tb{fill:var(--c4);transform-origin:0 0;animation:tb %sms linear infinite}"
           "@keyframes tb{%s}" % (dur.group(1), "".join(kf)))
    # Counter: one label per value, each visible until the next eat time.
    labels = [(0.0, 0)] + steps
    texts = []
    for i, (t, s) in enumerate(labels):
        end = labels[i + 1][0] if i + 1 < len(labels) else 100
        on = "%.2f%%,%.2f%%{opacity:1}" % (t + (0.02 if i else 0), end)
        before = "0%%,%.2f%%{opacity:0}" % t if i else ""
        after = "%.2f%%,100%%{opacity:0}" % (end + 0.02) if end < 100 else ""
        css += "@keyframes n%d{%s%s%s}.n%d{animation:n%d %sms linear infinite}" % (
            i, before, on, after, i, i, dur.group(1))
        texts.append('<text class="n n%d" x="%d" y="%.1f">%d / %d contributions</text>'
                     % (i, BAR_W + 16, y + 10, s, total))
    css += ".n{opacity:0;font:12px Georgia,'Times New Roman',serif;fill:%s}" % TEXT[theme]
    shapes = ('<rect x="0" y="%.1f" width="%d" height="12" rx="2" fill="%s"/>'
              '<rect class="tb" x="0" y="%.1f" width="%d" height="12" rx="2"/>%s'
              % (y, BAR_W, TRACK[theme], y, BAR_W, "".join(texts)))

    svg = strip_bar(svg)
    svg = svg.replace("</style>", css + "</style>", 1)
    return svg.replace("</svg>", shapes + "</svg>")


def main():
    user, pairs = sys.argv[1], sys.argv[2:]
    grid, total = calendar(user, os.environ["GITHUB_TOKEN"])
    for path, theme in zip(pairs[::2], pairs[1::2]):
        svg = open(path).read()
        try:
            out = tally(svg, grid, total, theme)
            print("%s: tally of %d contributions" % (path, total))
        except Exception as exc:
            out = strip_bar(svg)
            print("%s: bar removed (%s)" % (path, exc))
        with open(path, "w") as f:
            f.write(out)


if __name__ == "__main__":
    main()
