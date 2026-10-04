#!/usr/bin/env python3
"""
Contributions as a trading chart: weekly candlesticks of a 7-day rolling
contribution count ("price"), with weekly volume bars underneath.

    GITHUB_TOKEN=... python3 tools/candles.py USER OUTDIR [--weeks 26]

Writes OUTDIR/candles-dark.svg and OUTDIR/candles-light.svg. Standard library
only, so it runs as-is in a GitHub Action.
"""

import argparse
import datetime as dt
import json
import os
import urllib.request

THEMES = {
    "dark": dict(bg="#0d1117", grid="#21262d", text="#c9d1d9", muted="#8b949e",
                 up="#E8C46A", down="#a5533f", flat="#484f58", vol="#E8C46A"),
    "light": dict(bg="#ffffff", grid="#eaeef2", text="#24292f", muted="#57606a",
                  up="#b8892a", down="#b5503a", flat="#afb8c1", vol="#b8892a"),
}


def fetch_days(user, token):
    q = ('{ user(login: "%s") { contributionsCollection { contributionCalendar '
         '{ weeks { contributionDays { date contributionCount } } } } } }' % user)
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=json.dumps({"query": q}).encode(),
        headers={"Authorization": "bearer " + token, "Content-Type": "application/json",
                 "User-Agent": "candles"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(dt.date.fromisoformat(d["date"]), d["contributionCount"])
            for w in weeks for d in w["contributionDays"]]


def candles(days, n_weeks):
    counts = [c for _, c in days]
    rolling = [sum(counts[max(0, i - 6):i + 1]) for i in range(len(counts))]
    out = []
    # weeks end on the calendar's last day; walk back in 7-day blocks
    end = len(days)
    for _ in range(n_weeks):
        start = end - 7
        if start < 0:
            break
        seg = rolling[start:end]
        out.append(dict(date=days[start][0], o=seg[0], c=seg[-1], h=max(seg), l=min(seg),
                        v=sum(counts[start:end])))
        end = start
    return list(reversed(out))


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def render(cs, total, theme, user):
    t = THEMES[theme]
    W, H = 840, 292
    L, R, TOP = 44, 20, 80
    price_h, vol_h, gap = 140, 34, 14
    plot_w = W - L - R
    step = plot_w / max(1, len(cs))
    body = max(4.0, step * 0.56)
    hi = max([c["h"] for c in cs] + [1])
    vmax = max([c["v"] for c in cs] + [1])
    y = lambda v: TOP + price_h - v / hi * price_h
    vy0 = TOP + price_h + gap + vol_h

    last, first = cs[-1]["c"], cs[0]["o"]
    chg = last - cs[-2]["c"] if len(cs) > 1 else 0
    sign = "+" if chg >= 0 else "−"
    chg_col = t["up"] if chg > 0 else (t["down"] if chg < 0 else t["muted"])

    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
         'font-family="Georgia, \'Times New Roman\', serif">' % (W, H, W, H),
         '<rect width="100%%" height="100%%" rx="10" fill="%s"/>' % t["bg"],
         '<text x="%d" y="34" font-size="22" fill="%s">$DARYL</text>' % (L - 20, t["text"]),
         '<text x="%d" y="52" font-size="12" fill="%s">contributions · 7-day rolling · weekly candles</text>'
         % (L - 20, t["muted"]),
         '<text x="%d" y="34" font-size="22" text-anchor="end" fill="%s">%d</text>' % (W - R, t["text"], last),
         '<text x="%d" y="52" font-size="12" text-anchor="end" fill="%s">%s%d w/w · %d this year</text>'
         % (W - R, chg_col, sign, abs(chg), total)]
    for frac in (0, 0.5, 1):
        gy = TOP + price_h * (1 - frac)
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s"/>' % (L, W - R, gy, gy, t["grid"]))
        p.append('<text x="%d" y="%.1f" font-size="10" text-anchor="end" fill="%s">%d</text>'
                 % (L - 8, gy + 3, t["muted"], round(hi * frac)))
    last_month = None
    for i, c in enumerate(cs):
        cx = L + step * (i + 0.5)
        col = t["up"] if c["c"] > c["o"] else (t["down"] if c["c"] < c["o"] else t["flat"])
        p.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1.5"/>'
                 % (cx, cx, y(c["h"]), y(c["l"]), col))
        top, bot = y(max(c["o"], c["c"])), y(min(c["o"], c["c"]))
        p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1" fill="%s"/>'
                 % (cx - body / 2, top, body, max(1.5, bot - top), col))
        if c["v"]:
            vh = c["v"] / vmax * vol_h
            p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="0.35"/>'
                     % (cx - body / 2, vy0 - vh, body, vh, t["vol"]))
        if c["date"].month != last_month:
            last_month = c["date"].month
            p.append('<text x="%.1f" y="%d" font-size="10" text-anchor="middle" fill="%s">%s</text>'
                     % (cx, H - 12, t["muted"], c["date"].strftime("%b")))
    p.append('<title>%s</title></svg>' % esc("%s's contributions as weekly candles" % user))
    return "".join(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("user")
    ap.add_argument("outdir")
    ap.add_argument("--weeks", type=int, default=26)
    args = ap.parse_args()
    days = fetch_days(args.user, os.environ["GITHUB_TOKEN"])
    cs = candles(days, args.weeks)
    total = sum(c for _, c in days)
    os.makedirs(args.outdir, exist_ok=True)
    for theme in THEMES:
        path = os.path.join(args.outdir, "candles-%s.svg" % theme)
        with open(path, "w") as f:
            f.write(render(cs, total, theme, args.user))
        print("wrote", path)


if __name__ == "__main__":
    main()
