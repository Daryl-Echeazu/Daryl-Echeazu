#!/usr/bin/env python3
"""
A static "on repeat" card for one Spotify track: album art, title, artist.
No Spotify login: reads the track's public page. Rerun when the song changes.

    python3 tools/spotify_card.py TRACK_ID [--out assets]

Writes OUTDIR/on-repeat-dark.svg and OUTDIR/on-repeat-light.svg with the art
embedded, so GitHub never has to fetch anything from Spotify.
"""

import argparse
import base64
import html
import os
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (profile card generator)"}
THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", text="#e6edf3", muted="#8b949e", gold="#E8C46A"),
    "light": dict(bg="#ffffff", border="#d0d7de", text="#1f2328", muted="#57606a", gold="#b8892a"),
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def meta(page, prop):
    m = re.search(r'<meta property="og:%s" content="([^"]+)"' % prop, page)
    return html.unescape(m.group(1)) if m else ""


def card(theme, title, artist, album, art_b64):
    t = THEMES[theme]
    e = html.escape
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        'width="420" height="112" viewBox="0 0 420 112" font-family="Georgia, \'Times New Roman\', serif">'
        '<rect x="0.5" y="0.5" width="419" height="111" rx="10" fill="%s" stroke="%s"/>'
        '<clipPath id="a"><rect x="16" y="16" width="80" height="80" rx="6"/></clipPath>'
        '<image x="16" y="16" width="80" height="80" clip-path="url(#a)" '
        'href="data:image/jpeg;base64,%s"/>'
        '<text x="114" y="36" font-size="11" letter-spacing="0.5" fill="%s">On repeat</text>'
        '<text x="114" y="62" font-size="20" fill="%s">%s</text>'
        '<text x="114" y="84" font-size="13" fill="%s">%s · %s</text>'
        '<title>On repeat: %s by %s</title></svg>'
        % (t["bg"], t["border"], art_b64, t["gold"], t["text"], e(title), t["muted"], e(artist), e(album),
           e(title), e(artist)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("track_id")
    ap.add_argument("--out", default="assets")
    args = ap.parse_args()
    page = get("https://open.spotify.com/track/%s" % args.track_id).decode("utf-8", "replace")
    title = meta(page, "title")
    parts = [p.strip() for p in meta(page, "description").split("·")]
    artist, album = (parts + ["", ""])[:2]
    # 300px art (ab67616d00001e02...) is plenty for an 80px slot at 2x
    art_url = meta(page, "image").replace("ab67616d0000b273", "ab67616d00001e02")
    art = base64.b64encode(get(art_url)).decode()
    os.makedirs(args.out, exist_ok=True)
    for theme in THEMES:
        path = os.path.join(args.out, "on-repeat-%s.svg" % theme)
        with open(path, "w") as f:
            f.write(card(theme, title, artist, album, art))
        print("%s  %s — %s (%s)  %.0f KB" % (path, title, artist, album, os.path.getsize(path) / 1e3))


if __name__ == "__main__":
    main()
