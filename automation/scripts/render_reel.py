"""Render a voiced Instagram reel (1080x1920, 30 fps, H.264 + AAC) from a JSON spec: hook first, fast, and
every on-screen item synced to the voice.

    python3 render_reel.py spec.json OUT_DIR

This is the style Abr approved on 23 Oct 2026 (see automation/examples/thaaranira-cast-puzzle.json and the
"Reel style" section of PLAYBOOK.md). Writes reel.mp4, cover.jpg, reel.json and contact-sheet.jpg to OUT_DIR.

Spec:
{
  "game": "thaaranira" | null,           # null for a general Play Keralam reel
  "date": "YYYY-MM-DD",                  # the day it goes out; picks the voice and the music
  "voice": null,                         # leave null: alternates by week
  "scenes": [ {"type": ..., "beats": [...], ...fields}, ... ]
}

A scene is a list of BEATS. A beat is one short voice line ("say", Malayalam script only, 2-8 words) or a
silent hit ("dur": seconds). Each beat may name a sound ("sfx": pop | tick | whoosh | ding | boom | null);
sensible defaults are added per scene type. Items appear the moment their beat starts, and the scene cuts as
soon as its last beat ends plus a short tail ("tail", default 0.38 s). "min" sets a minimum scene length
(use it for scenes people must read, such as a story).

Scene types (fields; per-beat fields in [ ]):
  hook      [say, text, style: big|mid|tag|small]   kinetic lines; the first is already on screen at frame 0
  text      same as hook, for later scenes
  cards     headline, numbered (true), hidden (0) [say, text]   cards slam in one per beat (cast clues, facts)
  clues     = cards (cast clues)          steps = cards (numbered steps)
  countdown headline [say] then [dur, num]          "Got it?" then 3, 2, 1
  answer    kicker, big, chips[], detail, svg?, tiles? [say, question?]   white flash + ding on the reveal
  tiles     headline, sub, tiles[{text, color: green|yellow|grey|blue|cream|blank}] [say]
  story     headline, story [say]               one plot sentence on a card; set "min" so it can be read
  pair      headline, films[{title, director, cast[], date}], showDates, firstIndex [say, reveal?]
  map       headline, svg, place [say, place?]
  screen    headline, shot, caption [say]
  logos     headline, games[], highlight[] [say]
  cta       headline, shot?, side? [say]         url pill + "PLAY FREE · LINK IN BIO"

Language (Abr, 24 Oct 2026): the voice ("say") is Malayalam, but on-screen text is English. Only a
puzzle's own Malayalam content (a Vaakku word and its tiles, Paryayam synonyms) stays in Malayalam,
with its English meaning or transliteration beside it.

Malayalam: the pages carry NO lang="ml". With that tag Baloo Chettan 2 switches to its reformed-script
forms and splits every conjunct (ക്ക shows as ക്‌ക); without it the traditional kootaksharangal render.
Zero-width non-joiners (U+200C) in the text would split them too, so they are removed.
"""
import json
import pathlib
import re
import subprocess
import sys
import wave

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (BLUE, CONFIG, CREAM, GAMES, GREEN, INK, PINK, RED, YELLOW, YELLOW2,  # noqa: E402
                    badge_uri, fonts_head, game, is_dark, launch_chromium, logo_uri, shade)
from common import esc as _esc  # noqa: E402
import sound  # noqa: E402
from voice import speak, voice_for_week  # noqa: E402

W, H, FPS, SR = CONFIG["reels"]["width"], CONFIG["reels"]["height"], CONFIG["reels"]["fps"], 44100
GAP = 0.14        # silence between two voice beats in a scene
LEAD = 0.06       # before the first beat of a scene (0 for the very first scene)
TAIL = 0.38       # after the last beat, before the cut
ALL_GAMES = ["vaakku", "paryayam", "thaaranira", "katha", "aadyam", "ashwamedham",
             "antakshari", "kerala-guesser", "thurupp", "cidmoosa", "sat"]
WARN = []


def clean(text):
    t = str(text or "")
    if "‌" in t:
        WARN.append(f"removed a zero-width non-joiner from {t!r} (it splits conjuncts)")
        t = t.replace("‌", "")
    return t


def esc(text):
    return _esc(clean(text))


CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:#000}}
body{{font-family:'Baloo Chettan 2',sans-serif;color:{INK};-webkit-font-smoothing:antialiased}}
.reel{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:var(--b1);animation:punch .24s cubic-bezier(.2,1.2,.4,1) both}}
@keyframes punch{{from{{transform:scale(1.07)}}to{{transform:scale(1)}}}}
.spin{{position:absolute;left:50%;top:46%;width:3400px;height:3400px;margin:-1700px 0 0 -1700px;
  background:repeating-conic-gradient(from 0deg,var(--b1) 0deg 7deg,var(--b2) 7deg 14deg);animation:spin 18s linear infinite}}
.dots{{position:absolute;inset:0;background-color:var(--b1);background-image:radial-gradient(var(--b2) 6px,transparent 6.6px);background-size:54px 54px;animation:drift 5s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes drift{{to{{background-position:54px 108px}}}}
@keyframes slam{{0%{{transform:scale(1.9) rotate(var(--r,0deg));opacity:0}}55%{{transform:scale(.94) rotate(var(--r,0deg));opacity:1}}100%{{transform:scale(1) rotate(var(--r,0deg));opacity:1}}}}
@keyframes pop{{0%{{transform:scale(.4) rotate(var(--r,0deg));opacity:0}}65%{{transform:scale(1.08) rotate(var(--r,0deg));opacity:1}}100%{{transform:scale(1) rotate(var(--r,0deg));opacity:1}}}}
@keyframes inl{{from{{transform:translateX(-260px) rotate(var(--r,0deg));opacity:0}}70%{{transform:translateX(18px) rotate(var(--r,0deg));opacity:1}}to{{transform:translateX(0) rotate(var(--r,0deg));opacity:1}}}}
@keyframes inr{{from{{transform:translateX(260px) rotate(var(--r,0deg));opacity:0}}70%{{transform:translateX(-18px) rotate(var(--r,0deg));opacity:1}}to{{transform:translateX(0) rotate(var(--r,0deg));opacity:1}}}}
@keyframes up{{from{{transform:translateY(220px) rotate(var(--r,0deg));opacity:0}}to{{transform:translateY(0) rotate(var(--r,0deg));opacity:1}}}}
@keyframes gone{{to{{opacity:0;visibility:hidden}}}}
@keyframes flash{{from{{opacity:.95}}to{{opacity:0}}}}
@keyframes win{{from{{background:{CREAM};color:{INK}}}to{{background:{GREEN};color:#fff}}}}
@keyframes bar{{from{{width:0}}to{{width:100%}}}}
.slam{{opacity:0;animation:slam .3s cubic-bezier(.2,1.1,.4,1) var(--d,0s) both}}
.pop{{opacity:0;animation:pop .26s cubic-bezier(.2,1.5,.4,1) var(--d,0s) both}}
.inl{{opacity:0;animation:inl .26s cubic-bezier(.2,1.1,.4,1) var(--d,0s) both}}
.inr{{opacity:0;animation:inr .26s cubic-bezier(.2,1.1,.4,1) var(--d,0s) both}}
.up{{opacity:0;animation:up .3s cubic-bezier(.2,1.1,.4,1) var(--d,0s) both}}
.flash{{position:absolute;inset:0;background:#fff;z-index:9;animation:flash .3s ease-out both}}
.head{{position:absolute;left:60px;top:150px;right:180px;display:flex;align-items:center;gap:18px;z-index:5}}
.badge{{width:96px;height:96px;border-radius:50%;border:5px solid {INK};box-shadow:6px 6px 0 {INK};background:#fff}}
.chip{{color:{INK};display:flex;align-items:center;gap:12px;background:{CREAM};border:5px solid {INK};border-radius:999px;padding:8px 28px 4px 10px;box-shadow:6px 6px 0 {INK};font-weight:800;font-size:36px;white-space:nowrap}}
.chip img{{width:58px;height:58px;border-radius:14px;margin-top:-4px}}
.stage{{position:absolute;left:60px;right:160px;top:300px;bottom:420px;display:flex;flex-direction:column;justify-content:center;gap:34px;z-index:2}}
.stage>*{{flex:none}}
.stage.top{{justify-content:flex-start;padding-top:90px}}
.progress{{position:absolute;left:0;right:0;top:0;height:14px;background:rgba(0,0,0,.25);z-index:6}}
.progress i{{display:block;height:100%;background:{YELLOW};animation:bar var(--total) linear var(--start) both}}
.stroke{{-webkit-text-stroke:12px {INK};paint-order:stroke fill;text-shadow:12px 12px 0 {INK};color:var(--title)}}
.big{{font-weight:800;font-size:186px;line-height:1.06}}
.stage>.big.stroke{{white-space:nowrap}}
.mid{{font-weight:800;font-size:118px;line-height:1.12}}
.h2{{font-weight:800;font-size:92px;line-height:1.15}}
.tag{{align-self:flex-start;background:{PINK};color:{INK};border:8px solid {INK};border-radius:26px;box-shadow:12px 12px 0 {INK};padding:22px 38px 10px;font-weight:800;font-size:70px;line-height:1.2;--r:-3deg}}
.small{{font-family:'Manjari',sans-serif;font-weight:700;font-size:52px;line-height:1.3}}
.biglogo{{width:230px;height:230px;border-radius:54px;border:8px solid {INK};box-shadow:14px 14px 0 {INK};background:#fff;--r:-6deg}}
.cards{{display:flex;flex-direction:column;gap:24px}}
.card{{color:{INK};display:flex;align-items:center;gap:28px;background:{CREAM};border:8px solid {INK};border-radius:30px;box-shadow:12px 12px 0 {INK};padding:22px 34px 12px 22px;font-weight:800;font-size:var(--fs,76px);line-height:1.12}}
.card.plain{{padding-left:36px}}
.card .k{{flex:none;width:96px;height:96px;border-radius:50%;background:{YELLOW};border:7px solid {INK};display:flex;align-items:center;justify-content:center;font-size:56px;padding-top:8px}}
.card.hid{{background:{INK};color:{YELLOW2};letter-spacing:12px}}
.card.hid .k{{color:{INK};letter-spacing:0}}
.num{{position:absolute;left:0;right:0;top:820px;text-align:center;font-weight:800;font-size:520px;line-height:1;z-index:3}}
.num span{{display:inline-block}}
.chips{{display:flex;flex-wrap:wrap;gap:18px}}
.chips span{{color:{INK};background:{YELLOW};border:6px solid {INK};border-radius:999px;padding:14px 34px 6px;font-weight:800;font-size:50px;box-shadow:7px 7px 0 {INK}}}
.chips span:nth-child(2n){{background:{CREAM}}}
.box{{color:{INK};background:{CREAM};border:8px solid {INK};border-radius:30px;box-shadow:12px 12px 0 {INK};padding:26px 36px 16px}}
.tiles{{display:flex;flex-wrap:wrap;gap:22px;justify-content:center}}
.tile{{min-width:180px;height:180px;padding:24px 22px 0;border:8px solid {INK};border-radius:30px;box-shadow:10px 10px 0 {INK};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:92px;color:#fff}}
.t-green{{background:{GREEN}}} .t-yellow{{background:{YELLOW};color:{INK}}} .t-grey{{background:#9A958A}} .t-blue{{background:{BLUE}}}
.t-cream{{background:{CREAM};color:{INK}}}
.tiles.lg .tile{{min-width:220px;height:220px;font-size:112px}} .t-blank{{background:{CREAM};color:{INK};border-style:dashed}}
.film{{color:{INK};position:relative;background:{CREAM};border:8px solid {INK};border-radius:34px;box-shadow:12px 12px 0 {INK};padding:30px 36px 24px 150px}}
.film .ab{{color:{INK};position:absolute;left:30px;top:50%;margin-top:-50px;width:100px;height:100px;border-radius:50%;background:{YELLOW};border:7px solid {INK};font-weight:800;font-size:58px;display:flex;align-items:center;justify-content:center;padding-top:8px}}
.film .ti{{font-weight:800;font-size:68px;line-height:1.1}}
.film .me{{font-family:'Manjari',sans-serif;font-weight:700;font-size:36px;line-height:1.35;margin-top:6px}}
.film .dt{{display:inline-block;margin-top:14px;background:{INK};color:{YELLOW};border-radius:16px;padding:10px 20px 4px;font-weight:800;font-size:42px}}
.mapbox{{align-self:center}}
.mapbox svg{{height:700px;width:auto;border-radius:20px;filter:drop-shadow(12px 12px 0 {INK})}}
.answer .mapbox svg{{height:500px}}
@keyframes ping{{from{{transform:scale(.35);opacity:1}}to{{transform:scale(1.9);opacity:0}}}}
.mapbox [fill="#E8452C"]{{stroke:#E8452C;stroke-width:5}}
.mapbox .mark{{fill:none;stroke:#fff;stroke-width:5}}
.mapbox .ping{{fill:none;stroke:#E8452C;stroke-width:5;transform-box:fill-box;transform-origin:center;animation:ping .9s ease-out .35s infinite}}
.phone{{width:290px;height:628px;border-radius:62px;border:16px solid {INK};box-shadow:16px 16px 0 {INK};overflow:hidden;background:#000;--r:4deg}}
.phone.lg{{width:356px;height:770px;border-radius:68px;border-width:18px;align-self:center;--r:3deg}}
.phone img{{width:100%;height:100%;object-fit:cover;object-position:top}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:30px 26px}}
.gi{{display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;font-weight:800;font-size:36px;line-height:1.1}}
.gi img{{width:180px;height:180px;border-radius:42px;border:7px solid {INK};box-shadow:9px 9px 0 {INK};background:#fff}}
.url{{color:{INK};background:{YELLOW};border:9px solid {INK};border-radius:999px;box-shadow:14px 14px 0 {INK};padding:30px 20px 18px;text-align:center;font-weight:800;font-size:78px;--r:-2deg}}
.red{{align-self:center;background:{RED};color:{CREAM};border:7px solid {INK};border-radius:18px;padding:14px 34px 8px;font-weight:800;font-size:46px;--r:2deg;margin-top:-30px}}
.row{{display:flex;align-items:center;gap:40px}}
"""


def d(t):
    return f"--d:{t:.2f}s"


def at(ts, k, default):
    return ts[k] if k < len(ts) else default


def headline(s, t=0.0):
    return f'<div class="h2 stroke slam" style="{d(t)}">{esc(s["headline"])}</div>' if s.get("headline") else ""


def body_hook(s, ts, gid, first):
    out = []
    if s.get("logo") and gid:
        out.append(f'<img class="biglogo pop" style="{d(-0.1 if first else 0)}" src="{logo_uri(game(gid)["logo"])}">')
    for i, (b, t) in enumerate(zip(s["beats"], ts)):
        if not b.get("text"):
            continue
        style = b.get("style", "big")
        if first and i == 0 and t == 0:
            t = -0.14  # already landing on frame 0, so the reel never opens on an empty screen
        if style == "tag":
            out.append(f'<div class="tag pop" style="{d(t)}">{esc(b["text"])}</div>')
        elif style == "small":
            out.append(f'<div class="small up" style="{d(t)}">{esc(b["text"])}</div>')
        else:
            out.append(f'<div class="{style} stroke slam" style="{d(t)};--r:{-2 if i % 2 else 1.5}deg">{esc(b["text"])}</div>')
    return "".join(out)


def body_cards(s, ts):
    numbered = s.get("numbered", True)
    items = [(b, t) for b, t in zip(s["beats"], ts) if b.get("text") or b.get("name")]
    longest = max((len(clean(b.get("text") or b.get("name"))) for b, _ in items), default=10)
    fs = 76 if longest <= 14 else 64 if longest <= 20 else 54
    cards = ""
    for i, (b, t) in enumerate(items):
        k = f'<div class="k">{i + 1}</div>' if numbered else ""
        cards += (f'<div class="card inl{"" if numbered else " plain"}" style="{d(t)};--r:{(-1) ** i * 1.2}deg;--fs:{fs}px">'
                  f'{k}{esc(b.get("text") or b.get("name"))}</div>')
    last = items[-1][1] if items else 0
    n = len(items)
    cards += "".join(f'<div class="card hid inl" style="{d(last + 0.35 + j * 0.12)}"><div class="k">{n + j + 1}</div>? ? ? ?</div>'
                     for j in range(int(s.get("hidden", 0))))
    return f'{headline(s)}<div class="cards">{cards}</div>'


def body_countdown(s, ts, dur):
    out = f'<div class="big stroke slam" style="{d(at(ts, 0, 0))};--r:-2deg;font-size:160px">{esc(s.get("headline", "Got it?"))}</div>'
    nums = [(b, t) for b, t in zip(s["beats"], ts) if "num" in b]
    over = ""
    for j, (b, t) in enumerate(nums):
        end = nums[j + 1][1] if j + 1 < len(nums) else dur + 1
        over += (f'<div class="num"><span class="stroke" style="opacity:0;animation:pop .22s cubic-bezier(.2,1.5,.4,1) {t:.2f}s both,'
                 f'gone .01s linear {end:.2f}s forwards">{esc(b["num"])}</span></div>')
    return out, over


def tiles_html(tiles, start, step=0.09):
    return '<div class="tiles">' + "".join(
        f'<div class="tile pop t-{esc(t.get("color", "cream"))}" style="{d(start + i * step)}">{esc(t.get("text", ""))}</div>'
        for i, t in enumerate(tiles)) + "</div>"


def body_answer(s, ts):
    chips = "".join(f'<span class="pop" style="{d(0.32 + i * 0.1)}">{esc(c)}</span>' for i, c in enumerate(s.get("chips", [])))
    extra = ""
    if s.get("svg"):
        extra = f'<div class="mapbox up" style="{d(0.3)}">{s["svg"]}</div>'
    elif s.get("tiles"):
        extra = tiles_html(s["tiles"], 0.2)
    det = f'<div class="box up small" style="{d(0.5)};font-size:46px">{esc(s["detail"])}</div>' if s.get("detail") else ""
    q = "".join(f'<div class="tag pop" style="{d(t)};--r:-2deg">{esc(b["question"])}</div>'
                for b, t in zip(s["beats"], ts) if b.get("question"))
    kicker = f'<div class="h2 pop" style="{d(0)};color:var(--fg)">{esc(s["kicker"])}</div>' if s.get("kicker") else ""
    big = f'<div class="mid stroke slam" style="{d(0.06)};--r:-1.5deg">{esc(s["big"])}</div>' if s.get("big") else ""
    chips = f'<div class="chips">{chips}</div>' if chips else ""
    return f'<div class="answer" style="display:flex;flex-direction:column;gap:30px">{kicker}{big}{extra}{chips}{det}{q}</div>'


def body_tiles(s, ts):
    sub = f'<div class="box up small" style="{d(at(ts, 1, 0.45))};align-self:center;text-align:center">{esc(s["sub"])}</div>' if s.get("sub") else ""
    return f'{headline(s)}{tiles_html(s["tiles"], at(ts, 0, 0) + 0.12).replace("class=\"tiles\"", "class=\"tiles lg\"", 1)}{sub}'


def body_story(s, ts):
    return f'{headline(s)}<div class="box up" style="{d(at(ts, 0, 0) + 0.1)};--r:1deg"><div class="small" style="font-size:50px;line-height:1.42">{esc(s["story"])}</div></div>'


def body_pair(s, ts):
    reveal = next((t for b, t in zip(s["beats"], ts) if b.get("reveal")), None)
    films = []
    for i, f in enumerate(s["films"]):
        anim = ""
        if s.get("showDates") and s.get("firstIndex") == i and reveal is not None:
            anim = f";animation:inl .26s cubic-bezier(.2,1.1,.4,1) {at(ts, i, 0.3 * i):.2f}s both, win .2s linear {reveal:.2f}s both"
        elif s.get("showDates") and s.get("firstIndex") == i:
            anim = f";background:{GREEN};color:#fff"
        date = ""
        if s.get("showDates") and f.get("date"):
            dt_ = reveal if reveal is not None else 0.3
            date = f'<div class="dt pop" style="{d(dt_)}">{esc(f["date"])}</div>'
        meta = " · ".join(x for x in [f.get("director"), ", ".join(f.get("cast", [])[:2])] if x)
        films.append(f'<div class="film {"inl" if i == 0 else "inr"}" style="{d(at(ts, i, 0.3 * i))}{anim}"><div class="ab">{"AB"[i]}</div>'
                     f'<div class="ti">{esc(f["title"])}</div><div class="me">{esc(meta)}</div>{date}</div>')
    return f'{headline(s)}<div style="display:flex;flex-direction:column;gap:34px">{"".join(films)}</div>'


def body_map(s, ts):
    pt = next((t for b, t in zip(s["beats"], ts) if b.get("place")), at(ts, 1, 0.45))
    place = f'<div class="box pop" style="{d(pt)};--r:-2deg;align-self:flex-start"><div class="h2" style="font-size:72px">{esc(s["place"])}</div></div>' if s.get("place") else ""
    return f'{headline(s)}<div class="mapbox up" style="{d(at(ts, 0, 0) + 0.1)}">{s["svg"]}</div>{place}'


def body_screen(s, ts, spec_dir):
    shot = (spec_dir / s["shot"]).resolve()
    if not shot.exists():
        raise SystemExit(f"Missing screenshot {shot}")
    cap = f'<div class="box up small" style="{d(at(ts, 1, 0.6))};font-size:44px">{esc(s["caption"])}</div>' if s.get("caption") else ""
    return f'{headline(s)}<div class="phone lg up" style="{d(at(ts, 0, 0) + 0.08)}"><img src="file://{shot}"></div>{cap}'


def body_logos(s, ts):
    hi = set(s.get("highlight", []))
    start = at(ts, 0, 0) + 0.1
    cells = "".join(f'<div class="gi pop" style="{d(start + i * 0.06)}"><img src="{logo_uri(GAMES[g]["logo"])}" '
                    f'style="{"outline:9px solid " + YELLOW + ";outline-offset:6px" if g in hi else ""}"><div>{esc(GAMES[g]["en"])}</div></div>'
                    for i, g in enumerate(s.get("games") or ALL_GAMES))
    n = len(s.get("games") or ALL_GAMES)
    cols = ' style="grid-template-columns:repeat(2,1fr);max-width:640px"' if n in (2, 4) else ""  # 2x2, not 3+1
    return f'{headline(s)}<div class="grid"{cols}>{cells}</div>'


def body_cta(s, ts, gid, spec_dir):
    t1 = at(ts, 1, 0.45)
    if s.get("shot"):
        shot = (spec_dir / s["shot"]).resolve()
        if not shot.exists():
            raise SystemExit(f"Missing screenshot {shot}")
        mid = (f'<div class="row"><div class="phone up" style="{d(0.12)}"><img src="file://{shot}"></div>'
               f'<div class="small pop" style="{d(0.3)};color:var(--fg)">{esc(s.get("side", ""))}</div></div>')
    else:
        logo = logo_uri(game(gid)["logo"]) if gid else badge_uri()
        mid = (f'<div class="row"><img class="biglogo pop" style="{d(0.12)}" src="{logo}">'
               f'<div class="small pop" style="{d(0.3)};color:var(--fg)">{esc(s.get("side", ""))}</div></div>')
    return (f'<div class="h2 stroke slam" style="{d(at(ts, 0, 0))}">{esc(s.get("headline"))}</div>{mid}'
            f'<div class="url slam" style="{d(t1)}">{esc(CONFIG["brand"]["url"])}</div>'
            f'<div class="red pop" style="{d(t1 + 0.25)}">PLAY FREE · LINK IN BIO</div>')


# The guesser's answer map marks the place with a small red (#E8452C) shape; ring it so it reads on a phone.
MARK_JS = """<script>document.querySelectorAll('.mapbox svg').forEach(svg => {
  const hits = [...svg.querySelectorAll('[fill="#E8452C" i]')]; if (!hits.length) return;
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  hits.forEach(h => { const b = h.getBBox(); x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height); });
  const ns = 'http://www.w3.org/2000/svg', cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, r = Math.max(28, (x1 - x0) / 2 + 14);
  [['mark', r], ['ping', r]].forEach(([cls, rr]) => { const c = document.createElementNS(ns, 'circle');
    c.setAttribute('cx', cx); c.setAttribute('cy', cy); c.setAttribute('r', rr); c.setAttribute('class', cls); svg.appendChild(c); });
});</script>"""

# Big lines shrink until they fit the safe width (a long place or film name must never run off the edge).
# Run after the fonts have loaded.
FIT_JS = """() => { document.querySelectorAll('.stage .big, .stage .mid, .stage .h2').forEach(el => {
  let fs = parseFloat(getComputedStyle(el).fontSize);
  while (el.scrollWidth > el.clientWidth + 2 && fs > 56) { fs -= 4; el.style.fontSize = fs + 'px'; } }); return true; }"""

LOOKS = {"hook": "accent", "answer": "accent", "cta": "accent", "countdown": "yellow"}


def scene_html(s, i, gid, ts, dur, start, total, spec_dir):
    accent = game(gid)["color"] if gid else BLUE
    t = s["type"]
    look = LOOKS.get(t, "pale" if i % 2 else "soft")
    b1, b2, kind = {"accent": (accent, shade(accent, 1.14), "spin"), "yellow": (YELLOW, YELLOW2, "spin"),
                    "pale": (shade(accent, 1.78), shade(accent, 1.6), "dots"),
                    "soft": (shade(accent, 1.55), shade(accent, 1.4), "dots")}[look]
    fg = CREAM if is_dark(b1) else INK
    title = YELLOW if is_dark(b1) else CREAM
    over, flash, top = "", "", False
    if t in ("hook", "text"):
        body = body_hook(s, ts, gid, i == 0)
    elif t in ("cards", "clues", "steps"):
        body = body_cards(s, ts)
    elif t == "countdown":
        body, over = body_countdown(s, ts, dur)
        top = True
    elif t == "answer":
        body, flash = body_answer(s, ts), '<div class="flash"></div>'
    elif t == "tiles":
        body = body_tiles(s, ts)
    elif t == "story":
        body = body_story(s, ts)
    elif t == "pair":
        body = body_pair(s, ts)
    elif t == "map":
        body = body_map(s, ts)
    elif t == "screen":
        body = body_screen(s, ts, spec_dir)
    elif t == "logos":
        body = body_logos(s, ts)
    elif t == "cta":
        body = body_cta(s, ts, gid, spec_dir)
    else:
        raise SystemExit(f"Unknown scene type '{t}'")
    head = (f'<img src="{logo_uri(game(gid)["logo"])}">{esc(game(gid)["en"])}' if gid
            else f'{esc(CONFIG["brand"]["name_en"])}')
    # NB: no lang="ml" on <html> (it splits conjuncts in Baloo Chettan 2).
    return (f'<!doctype html><html><head><meta charset="utf-8">{fonts_head()}<style>{CSS}</style></head><body>'
            f'<div class="reel" style="--b1:{b1};--b2:{b2};--title:{title};--fg:{fg};color:{fg}"><div class="{kind}"></div>'
            f'<div class="progress"><i style="--total:{total:.2f}s;--start:-{start:.2f}s"></i></div>'
            f'<div class="head"><img class="badge" src="{badge_uri()}"><div class="chip">{head}</div></div>'
            f'<div class="stage{" top" if top else ""}">{body}</div>{over}{flash}</div>{MARK_JS}</body></html>')


def default_sfx(scene_type, scene_index, beat_index, beat):
    if "sfx" in beat:
        return beat["sfx"]
    if "num" in beat:
        return "tick"
    if scene_type in ("hook", "text"):
        return "boom" if scene_index == 0 and beat_index == 0 else ("pop" if beat.get("text") else None)
    if scene_type == "answer":
        return "ding" if beat_index == 0 else None
    if scene_type in ("cards", "clues", "steps", "countdown", "cta"):
        return "pop"
    if scene_type == "pair" and beat.get("reveal"):
        return "ding"
    if scene_type in ("map", "pair", "tiles") and beat_index <= 1:
        return "pop"
    return None


SFX_GAIN = {"pop": 0.35, "tick": 0.5, "ding": 0.45, "boom": 0.5, "whoosh": 0.3}


def lint(spec):
    for si, s in enumerate(spec["scenes"]):
        for b in s.get("beats", []):
            say = b.get("say") or ""
            if re.search(r"[A-Za-z0-9]", say):
                WARN.append(f"scene {si + 1}: say line has Latin letters or digits (the voice garbles them): {say!r}")
            if len(say.split()) > 9:
                WARN.append(f"scene {si + 1}: say line is {len(say.split())} words; keep beats to 2-8 words: {say!r}")
        if not s.get("beats"):
            raise SystemExit(f"scene {si + 1} ({s.get('type')}) has no beats")
    if spec["scenes"][0]["type"] != "hook":
        WARN.append("the first scene is not a hook; reels must open with the hook")


def resample(x, sr_from, sr_to):
    if sr_from == sr_to:
        return x
    n = int(len(x) * sr_to / sr_from)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def render(spec_path, out_dir):
    spec_dir = pathlib.Path(spec_path).resolve().parent
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    lint(spec)
    out = pathlib.Path(out_dir).resolve()
    frames = out / ".frames"
    htmld = out / ".html"
    for p in (out, frames, htmld):
        p.mkdir(parents=True, exist_ok=True)
    for old in frames.glob("*.jpg"):
        old.unlink()
    gid = spec.get("game")
    voice = spec.get("voice") or voice_for_week(spec["date"])

    # 1. Voice per beat, then the beat times inside each scene.
    plan = []
    for si, s in enumerate(spec["scenes"]):
        t = 0.0 if si == 0 else LEAD
        ts, auds = [], []
        for b in s["beats"]:
            if b.get("say"):
                a, sr = speak(clean(b["say"]), voice)
                a = resample(a, sr, SR)
                length = len(a) / SR
            else:
                a, length = np.zeros(0, np.float32), float(b.get("dur", 0.55))
            ts.append(t)
            auds.append(a)
            t += length + (float(b.get("gap", GAP)) if b.get("say") else 0)
        if s["beats"][-1].get("say"):
            t -= float(s["beats"][-1].get("gap", GAP))
        dur = max(float(s.get("min", 0)), t + float(s.get("tail", 0.05 if s["type"] == "countdown" else TAIL)))
        plan.append((ts, auds, dur))
    durs = [p[2] for p in plan]
    total = sum(durs)
    lo, hi = CONFIG["reels"]["minSeconds"], CONFIG["reels"]["maxSeconds"]
    if not lo <= total <= hi:
        WARN.append(f"reel is {total:.1f}s; aim for {lo}-{hi}s (add or cut beats)")

    # 2. Audio: voice + effects over a music bed that ducks under the voice.
    n = int(total * SR) + SR
    vox = np.zeros(n, np.float32)
    fx = np.zeros(n, np.float32)
    start = 0.0
    for si, (s, (ts, auds, dur)) in enumerate(zip(spec["scenes"], plan)):
        if si > 0:
            w = sound.whoosh()
            a0 = int(max(0, start - 0.16) * SR)
            fx[a0:a0 + len(w)] += w[: n - a0] * 0.22
        for bi, (b, t, a) in enumerate(zip(s["beats"], ts, auds)):
            a0 = int((start + t) * SR)
            vox[a0:a0 + len(a)] += a[: n - a0]
            name = default_sfx(s["type"], si, bi, b)
            if name:
                e = sound.SFX[name]()
                fx[a0:a0 + len(e)] += e[: n - a0] * float(b.get("sfxGain", SFX_GAIN.get(name, 0.35)))
        start += dur
    seed = int(spec.get("date", "2026-01-01").replace("-", "")) % 1000
    bed = np.zeros(n, np.float32)
    m = sound.bed(total + 0.2, seed=seed, bpm=int(spec.get("bpm", 124)))
    bed[: min(n, len(m))] = m[:n]
    env = np.convolve(np.abs(vox), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    env = np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
    end = int(total * SR)
    fade = np.ones(n, np.float32)
    fl = int(0.25 * SR)
    fade[end - fl:end] = np.linspace(1, 0, fl)
    fade[end:] = 0
    mix = ((vox + fx + bed * (0.42 - 0.27 * env)) * fade)[:end]
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.97
    with wave.open(str(out / ".mix.wav"), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((mix * 32767).astype(np.int16).tobytes())

    # 3. Frames: each scene's CSS animations stepped frame by frame.
    k = 0
    start = 0.0
    sheet = []
    with sync_playwright() as p:
        browser = launch_chromium(p)
        page = browser.new_page(viewport={"width": W, "height": H})
        for si, (s, (ts, auds, dur)) in enumerate(zip(spec["scenes"], plan)):
            path = htmld / f"scene-{si + 1}.html"
            path.write_text(scene_html(s, si, gid, ts, dur, start, total, spec_dir), encoding="utf-8")
            page.goto(f"file://{path}")
            page.evaluate("document.fonts.ready.then(() => true)")
            page.wait_for_timeout(150)
            page.evaluate(FIT_JS)
            nf = int(round(dur * FPS))
            marks = {min(nf - 1, int((t + 0.45) * FPS)) for t in ts[1:]} | {nf - 1}
            for f in range(nf):
                ms = f * 1000 / FPS
                page.evaluate("(ms) => document.getAnimations().forEach(a => { a.pause(); a.currentTime = ms; })", ms)
                fp = frames / f"{k:05d}.jpg"
                page.screenshot(path=str(fp), type="jpeg", quality=92)
                if f in marks:
                    sheet.append(fp)
                k += 1
            # measured on the last frame, when every item has landed (mid-animation scaling would inflate it)
            overflow = page.evaluate("""() => { const s = document.querySelector('.stage').getBoundingClientRect();
                return [...document.querySelectorAll('.stage > *')].some(c => { const r = c.getBoundingClientRect();
                  return r.top < s.top - 24 || r.bottom > s.bottom + 24 || r.left < s.left - 24 || r.right > s.right + 24; }); }""")
            if overflow:
                WARN.append(f"scene {si + 1} ({s['type']}): content is taller or wider than the safe area; shorten text or drop an item")
            start += dur
        browser.close()

    # 4. Encode, cover, contact sheet.
    mp4 = out / "reel.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(frames / "%05d.jpg"),
                    "-i", str(out / ".mix.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-shortest", "-movflags", "+faststart", str(mp4)],
                   check=True)
    cover_ms = int(max(0.5, durs[0] - 0.1) * 1000)  # the end of the hook, with every hook line on screen
    Image.open(frames / f"{min(k - 1, int(cover_ms / 1000 * FPS)):05d}.jpg").save(out / "cover.jpg", quality=92)
    cols = 6
    rows = (len(sheet) + cols - 1) // cols
    img = Image.new("RGB", (cols * 278 - 8, rows * 488 - 8), "white")
    for j, fp in enumerate(sheet):
        img.paste(Image.open(fp).resize((270, 480)), ((j % cols) * 278, (j // cols) * 488))
    img.save(out / "contact-sheet.jpg", quality=88)
    words = sum(len(b["say"].split()) for s in spec["scenes"] for b in s["beats"] if b.get("say"))
    info = {"file": str(mp4), "seconds": round(total, 2), "coverMs": cover_ms, "voice": voice, "words": words,
            "scenes": [round(x, 2) for x in durs], "frames": k}
    (out / "reel.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    for w in WARN:
        print("WARNING:", w)
    print(json.dumps(info))
    return info


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    render(sys.argv[1], sys.argv[2])
