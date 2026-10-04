#!/usr/bin/env python3
"""
Lighthouse scores for darylecheazu.me as four rings, from a Lighthouse JSON
report (the workflow runs `npx lighthouse` and passes its output here).

    python3 tools/lighthouse_card.py report.json OUTDIR

Writes OUTDIR/lighthouse-dark.svg and OUTDIR/lighthouse-light.svg.
"""

import datetime as dt
import json
import math
import os
import sys

CATS = [("performance", "Performance"), ("accessibility", "Accessibility"),
        ("best-practices", "Best practices"), ("seo", "SEO")]
THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", text="#e6edf3", muted="#8b949e",
                 track="#21262d", good="#E8C46A", ok="#c9a24a", bad="#a5533f"),
    "light": dict(bg="#ffffff", border="#d0d7de", text="#1f2328", muted="#57606a",
                  track="#eaeef2", good="#b8892a", ok="#a07a2a", bad="#b5503a"),
}


def render(scores, when, theme, site):
    t = THEMES[theme]
    W, H, r = 520, 150, 26
    circ = 2 * math.pi * r
    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
         'font-family="Georgia, \'Times New Roman\', serif">' % (W, H, W, H),
         '<rect x="0.5" y="0.5" width="%d" height="%d" rx="10" fill="%s" stroke="%s"/>'
         % (W - 1, H - 1, t["bg"], t["border"]),
         '<text x="20" y="28" font-size="13" fill="%s">%s</text>' % (t["text"], site),
         '<text x="%d" y="28" font-size="11" text-anchor="end" fill="%s">Lighthouse · mobile · %s</text>'
         % (W - 20, t["muted"], when)]
    for i, (key, label) in enumerate(CATS):
        s = scores.get(key)
        cx, cy = 20 + 60 + i * 120, 82
        col = t["good"] if s is not None and s >= 90 else (t["ok"] if s is not None and s >= 50 else t["bad"])
        frac = (s or 0) / 100
        p.append('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="5"/>'
                 % (cx, cy, r, t["track"]))
        p.append('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="5" '
                 'stroke-linecap="round" stroke-dasharray="%.1f %.1f" transform="rotate(-90 %d %d)"/>'
                 % (cx, cy, r, col, circ * frac, circ, cx, cy))
        p.append('<text x="%d" y="%d" font-size="17" text-anchor="middle" fill="%s">%s</text>'
                 % (cx, cy + 6, t["text"], "–" if s is None else s))
        p.append('<text x="%d" y="%d" font-size="11" text-anchor="middle" fill="%s">%s</text>'
                 % (cx, cy + r + 22, t["muted"], label))
    p.append("<title>Lighthouse scores for %s</title></svg>" % site)
    return "".join(p)


def main():
    report, outdir = sys.argv[1], sys.argv[2]
    with open(report) as f:
        lh = json.load(f)
    cats = lh["categories"]
    scores = {k: round(cats[k]["score"] * 100) for k, _ in CATS if cats.get(k, {}).get("score") is not None}
    when = dt.date.fromisoformat(lh["fetchTime"][:10]).strftime("%b %-d, %Y")
    site = lh.get("finalDisplayedUrl", lh.get("requestedUrl", "")).replace("https://", "").rstrip("/")
    os.makedirs(outdir, exist_ok=True)
    for theme in THEMES:
        path = os.path.join(outdir, "lighthouse-%s.svg" % theme)
        with open(path, "w") as f:
            f.write(render(scores, when, theme, site))
        print("wrote", path, scores)


if __name__ == "__main__":
    main()
