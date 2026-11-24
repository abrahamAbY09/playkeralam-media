"""The "race" reel look (added 24 Nov 2026 for the B style rules): a sports-broadcast / race HUD. A hot orange-red
field with black diagonal slabs sliding through it and white speed streaks, huge condensed white type (Anton,
Baloo Chettan 2 for Malayalam) with a hard black drop, lime-on-black tags, a big outlined lap number drifting
behind, and a row of four "lap" boxes that tick off one puzzle at a time. Made for challenge and race-style
reels (the daily four, weekend challenges, streaks, speed rounds). All text sits inside Meta's Reels safe zone
(y 270-1250, x 65-960). No sunburst, dots, cream cards, badge pill, CTA pill or floating phone.

Use it with "theme": "race" in a reel spec. render_reel.py calls scene_html() below for every scene.

Scene types (scene fields; per-beat fields in [ ]):
  hook / text  laps?, lap?  [say, text, style: big|tag|mid, showLaps]   lines slam in; the first is on screen at
               frame 0. "laps" (int, e.g. 4) shows the lap boxes with the beat that has "showLaps": true.
  triangle     laps, lap, names[3]  [say, text, node, lines, timer, sfx, dur]   a love-triangle (or any 3-way)
               diagram fills the frame: a beat with "node": k lights vertex k, "lines": true draws the edges,
               "timer": true starts a draining bar to the end of the scene (add silent "dur" beats with
               "sfx": "tick" for the thinking window). One caption per beat, each replacing the last.
  reveal       title, sub, laps, done  [say, text, tick]   lime flash, the answer slams in; a beat with
               "tick": true fills the next lap box with a check and shows its caption.
  loop         laps  [say, text, url, echo, clear]   share trigger + playkeralam.com; an "echo" beat clears the
               stage and brings back the hook's line over empty lap boxes, so a replay flows on.
Palette: orange #FF5A1F -> red #D9241B, black #0E0E0E, white #FFFFFF, lime #C8FF3C.
"""
import re

from common import esc as _esc

ORANGE, RED, BLACK, WHITE, LIME = "#FF5A1F", "#D9241B", "#0E0E0E", "#FFFFFF", "#C8FF3C"
SAFE = dict(top=270, bottom=1250, left=65, right=960)
PAD = 12
STAGE_W = SAFE['right'] - SAFE['left'] - 2 * PAD

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:{RED}}}
body{{font-family:'Anton','Baloo Chettan 2',sans-serif;color:{WHITE};-webkit-font-smoothing:antialiased}}
.reel{{position:relative;width:1080px;height:1920px;overflow:hidden;background:linear-gradient(165deg,{ORANGE} 0%,#F23E1C 45%,{RED} 100%)}}
.band{{position:absolute;left:-600px;width:2400px;background:{BLACK};transform:rotate(-14deg)}}
.b1{{top:1400px;height:900px;animation:b1 var(--dur) linear both}}
.b2{{top:80px;height:120px;opacity:.88;animation:b2 var(--dur) linear both}}
.b3{{top:1340px;height:22px;background:{LIME};animation:b1 var(--dur) linear both}}
@keyframes b1{{from{{transform:rotate(-14deg) translateX(-40px)}}to{{transform:rotate(-14deg) translateX(60px)}}}}
@keyframes b2{{from{{transform:rotate(-14deg) translateX(80px)}}to{{transform:rotate(-14deg) translateX(-90px)}}}}
.streaks{{position:absolute;inset:-200px;transform:rotate(-14deg);
  background:repeating-linear-gradient(0deg,transparent 0 46px,rgba(255,255,255,.16) 46px 50px,transparent 50px 131px,rgba(255,255,255,.08) 131px 133px);
  -webkit-mask-image:linear-gradient(90deg,transparent,#000 30%,#000 70%,transparent);animation:streak .7s linear infinite}}
@keyframes streak{{from{{transform:rotate(-14deg) translateX(-260px)}}to{{transform:rotate(-14deg) translateX(260px)}}}}
.ghost{{position:absolute;right:-60px;top:330px;font-family:'Anton';font-size:820px;line-height:1;color:transparent;
  -webkit-text-stroke:8px rgba(255,255,255,.20);animation:gh var(--dur) linear both}}
@keyframes gh{{from{{transform:translateX(40px) skewX(-8deg)}}to{{transform:translateX(-70px) skewX(-8deg)}}}}
.stage{{position:absolute;left:{SAFE['left'] + PAD}px;top:{SAFE['top'] + PAD}px;width:{STAGE_W}px;
  height:{SAFE['bottom'] - SAFE['top'] - 2 * PAD}px;display:flex;flex-direction:column;justify-content:center;gap:38px;z-index:3;
  animation:push var(--dur) linear both;transform-origin:50% 50%}}
.stage>*{{flex:none}}
@keyframes push{{from{{transform:scale(1)}}to{{transform:scale(1.025)}}}}
.big{{font-family:'Anton','Baloo Chettan 2';font-size:200px;line-height:.98;text-transform:uppercase;letter-spacing:1px;
  text-shadow:10px 10px 0 {BLACK};white-space:nowrap}}
.big.xl{{font-size:260px}}
.mid{{font-family:'Anton','Baloo Chettan 2';font-size:132px;line-height:1.02;text-transform:uppercase;text-shadow:8px 8px 0 {BLACK}}}
.tag{{align-self:flex-start;font-family:'Anton','Baloo Chettan 2';font-size:120px;line-height:1.12;text-transform:uppercase;color:{LIME};
  background:{BLACK};padding:14px 34px 6px;transform:skewX(-8deg);white-space:nowrap}}
.ml{{font-family:'Baloo Chettan 2';font-weight:800;text-transform:none}}
.slam{{opacity:0;animation:slam .3s cubic-bezier(.2,1.1,.35,1) var(--d,0s) both}}
@keyframes slam{{0%{{opacity:0;transform:translateX(-220px) skewX(-18deg)}}70%{{opacity:1;transform:translateX(14px) skewX(-4deg)}}100%{{opacity:1;transform:none}}}}
.tag.slam{{animation-name:slamT}}
@keyframes slamT{{0%{{opacity:0;transform:translateX(-220px) skewX(-24deg)}}70%{{opacity:1;transform:translateX(14px) skewX(-8deg)}}100%{{opacity:1;transform:skewX(-8deg)}}}}
.zoom{{opacity:0;animation:zoom .34s cubic-bezier(.2,1.2,.35,1) var(--d,0s) both}}
@keyframes zoom{{0%{{opacity:0;transform:scale(2.2)}}100%{{opacity:1;transform:scale(1)}}}}
@keyframes show{{to{{opacity:1}}}}
@keyframes hide{{to{{opacity:0;visibility:hidden}}}}
.laps{{display:flex;gap:26px;justify-content:flex-start}}
.lap{{width:150px;height:150px;border:10px solid {WHITE};background:rgba(14,14,14,.35);transform:skewX(-8deg);position:relative;
  opacity:0;animation:zoom .3s cubic-bezier(.2,1.2,.35,1) var(--d,0s) both}}
.lap.cur{{border-color:{LIME};box-shadow:0 0 0 8px rgba(200,255,60,.35)}}
.lap.cur::before{{content:"";position:absolute;inset:-10px;border:10px solid {LIME};animation:pulse .6s ease-in-out infinite alternate}}
@keyframes pulse{{from{{opacity:.2}}to{{opacity:1}}}}
.lap .fill{{position:absolute;inset:0;background:{LIME};transform-origin:0 50%;transform:scaleX(0);animation:fillx .28s ease-out var(--f) both}}
.lap .chk{{position:absolute;left:28px;top:18px;width:62px;height:100px;border-right:18px solid {BLACK};border-bottom:18px solid {BLACK};
  transform:rotate(40deg) scale(0);transform-origin:50% 50%;animation:chk .26s cubic-bezier(.2,1.6,.4,1) var(--f) both}}
.lap.done .fill{{animation:none;transform:none}}
.lap.done .chk{{animation:none;transform:rotate(40deg) scale(1)}}
@keyframes fillx{{to{{transform:scaleX(1)}}}}
@keyframes chk{{to{{transform:rotate(40deg) scale(1)}}}}
.tri{{position:relative;height:540px}}
.laps.sm .lap{{width:110px;height:110px;border-width:8px}}
.stage.tight{{gap:26px}}
.tri svg{{position:absolute;inset:0;width:100%;height:100%;overflow:visible}}
.edge{{fill:none;stroke:{WHITE};stroke-width:16;stroke-linecap:round;stroke-dasharray:1400;stroke-dashoffset:1400;
  animation:draw .5s ease-out var(--d) forwards}}
.edge.hot{{stroke:{LIME};stroke-dasharray:28 26;stroke-dashoffset:0;opacity:0;animation:show .01s linear var(--d) forwards,march .6s linear infinite}}
@keyframes draw{{to{{stroke-dashoffset:0}}}}
@keyframes march{{to{{stroke-dashoffset:-54}}}}
.node{{position:absolute;width:300px;height:330px;margin:-130px 0 0 -150px;justify-content:flex-start;padding-top:40px;display:flex;flex-direction:column;align-items:center;justify-content:center;
  opacity:0;animation:zoom .32s cubic-bezier(.2,1.3,.35,1) var(--d) both}}
.heart{{width:150px;height:150px;flex:none;position:relative;transform:rotate(-45deg);animation:beat .5s ease-in-out infinite alternate}}
.heart i{{position:absolute;left:-5px;top:20px;width:150px;height:150px;background:{BLACK};border:0}}
.heart i::before,.heart i::after{{content:"";position:absolute;width:150px;height:150px;border-radius:50%;background:{BLACK}}}
.heart i::before{{top:-75px;left:0}}
.heart i::after{{left:75px;top:0}}
.node.on .heart i,.node.on .heart i::before,.node.on .heart i::after{{background:{LIME}}}
@keyframes beat{{from{{transform:rotate(-45deg) scale(.94)}}to{{transform:rotate(-45deg) scale(1.06)}}}}
.nlab{{font-family:'Anton';font-size:84px;line-height:1;text-transform:uppercase;color:{BLACK};background:{WHITE};padding:8px 22px 2px;transform:skewX(-8deg);margin-top:40px;white-space:nowrap}}
.node.on .nlab{{background:{LIME}}}
.timer{{position:relative;height:46px;background:{BLACK};transform:skewX(-8deg);overflow:hidden;border:6px solid {BLACK}}}
.timer i{{position:absolute;left:0;top:0;bottom:0;right:0;background:{LIME};transform-origin:0 50%;
  animation:drain var(--len) linear var(--d) both,warn var(--len) steps(1) var(--d) both}}
.timer.idle i{{animation:none}}
@keyframes drain{{from{{transform:scaleX(1)}}to{{transform:scaleX(0)}}}}
@keyframes warn{{0%,60%{{background:{LIME}}}61%,100%{{background:{WHITE}}}}}
.slot{{position:relative}}
.slot>*{{position:absolute;left:0;right:0;top:0}}
.url{{font-family:'Anton';font-size:128px;line-height:1.1;color:{BLACK};background:{LIME};padding:12px 30px 4px;transform:skewX(-8deg);
  align-self:flex-start;white-space:nowrap}}
.sub{{font-family:'Anton';font-size:96px;line-height:1;color:{LIME};text-shadow:6px 6px 0 {BLACK}}}
.flash{{position:absolute;inset:0;background:{LIME};z-index:9;opacity:0;animation:fl .32s ease-out var(--d,0s) both}}
@keyframes fl{{0%{{opacity:.95}}100%{{opacity:0}}}}
"""


def esc(t):
    return _esc(str(t or "").replace("‌", ""))


def d(t):
    return f"--d:{t:.2f}s"


def rich(text):
    out = esc(text).replace("\n", "<br>")
    return re.sub(r"([ഀ-ൿ]+)", r'<span class="ml">\1</span>', out)


def vis(t, end, last):
    return f"opacity:0;animation:show .01s linear {t:.2f}s forwards" + ("" if last else f",hide .01s linear {end:.2f}s forwards")


def line(b, t):
    style = b.get("style", "big")
    cls = {"big": "big fit", "xl": "big xl fit", "mid": "mid fit", "tag": "tag fit"}.get(style, "big fit")
    return f'<div class="{cls} slam" style="{d(t)}">{rich(b["text"])}</div>'


def laps_row(n, t0, cur=None, done=0, tick_at=None):
    cells = []
    for k in range(n):
        cls = "lap"
        inner = ""
        if k < done:
            cls += " done"
            inner = '<div class="fill"></div><div class="chk"></div>'
        elif tick_at is not None and k == done:
            inner = f'<div class="fill" style="--f:{tick_at:.2f}s"></div><div class="chk" style="--f:{tick_at + 0.12:.2f}s"></div>'
        if cur is not None and k == cur and tick_at is None:
            cls += " cur"
        cells.append(f'<div class="{cls}" style="{d(t0 + k * 0.06)}">{inner}</div>')
    return f'<div class="laps">{"".join(cells)}</div>'


def hook(s, ts, dur, first):
    out = []
    for i, (b, t) in enumerate(zip(s["beats"], ts)):
        if first and i == 0 and t == 0:
            t = -0.4  # fully landed on frame 0
        if b.get("showLaps") and s.get("laps"):
            out.append(laps_row(int(s["laps"]), t, cur=s.get("lap")))
        if b.get("text"):
            out.append(line(b, t))
    return "".join(out)


def captions(s, ts, dur, height):
    caps = []
    texted = [(b, t) for b, t in zip(s["beats"], ts) if b.get("text")]
    for j, (b, t) in enumerate(texted):
        end = texted[j + 1][1] if j + 1 < len(texted) else dur + 5
        cls = {"tag": "tag", "mid": "mid"}.get(b.get("style", "mid"), "mid")
        caps.append(f'<div style="{vis(t, end, j == len(texted) - 1)}"><div class="{cls} fit slam" style="{d(t)}">{rich(b["text"])}</div></div>')
    return f'<div class="slot" style="height:{height}px">{"".join(caps)}</div>'


def triangle(s, ts, dur):
    names = s.get("names", ["", "?", "?"])
    pts = [(436, 95), (150, 345), (722, 345)]  # node anchors inside the stage box (width ~871, height 540)
    node_t = {}
    lines_t = None
    tstart = None
    for b, t in zip(s["beats"], ts):
        for k in ([b["node"]] if isinstance(b.get("node"), int) else b.get("node") or []):
            node_t.setdefault(k, t)
        if b.get("lines") and lines_t is None:
            lines_t = t
        if b.get("timer") and tstart is None:
            tstart = t
    lt = lines_t if lines_t is not None else dur + 5
    edges = []
    for a, c in ((0, 1), (0, 2), (1, 2)):
        x1, y1 = pts[a]
        x2, y2 = pts[c]
        cls = "edge hot" if (a, c) == (1, 2) else "edge"
        edges.append(f'<path class="{cls}" style="--d:{lt + (0.25 if cls == "edge hot" else 0):.2f}s" d="M{x1},{y1} L{x2},{y2}"/>')
    nodes = []
    for k, (x, y) in enumerate(pts):
        t = node_t.get(k, lt + 0.1 * k if lines_t is not None else dur + 5)
        on = " on" if k == 0 else ""
        nodes.append(f'<div class="node{on}" style="left:{x}px;top:{y}px;{d(t)}"><div class="heart"><i></i></div>'
                     f'<div class="nlab">{esc(names[k])}</div></div>')
    svg = f'<svg viewBox="0 0 871 540">{"".join(edges)}</svg>'
    laps = laps_row(int(s.get("laps", 4)), ts[0] - 0.5, cur=s.get("lap", 0)).replace('class="laps"', 'class="laps sm"') if s.get("laps") else ""
    if tstart is None:
        timer = '<div class="timer idle"><i></i></div>'
    else:
        timer = f'<div class="timer"><i style="{d(tstart)};--len:{max(0.5, dur - tstart - 0.05):.2f}s"></i></div>'
    return f'{laps}<div class="tri">{svg}{"".join(nodes)}</div>{timer}{captions(s, ts, dur, 160)}'


def reveal(s, ts, dur):
    t0 = ts[0]
    title = f'<div class="big xl fit zoom" style="{d(t0 + 0.05)}">{esc(s.get("title", ""))}</div>'
    sub = f'<div class="sub slam" style="{d(t0 + 0.2)}">{esc(s.get("sub", ""))}</div>' if s.get("sub") else ""
    tick = next((t for b, t in zip(s["beats"], ts) if b.get("tick")), None)
    laps = laps_row(int(s.get("laps", 4)), t0 - 0.5, done=int(s.get("done", 0)), tick_at=tick) if s.get("laps") else ""
    rest = [(b, t) for b, t in list(zip(s["beats"], ts))[1:] if b.get("text")]
    more = "".join(f'<div class="tag fit slam" style="{d(t)}">{rich(b["text"])}</div>' for b, t in rest)
    first = s["beats"][0]
    head = f'<div class="tag slam" style="{d(t0)}">{rich(first["text"])}</div>' if first.get("text") else ""
    return f'{head}{title}{sub}{laps}{more}'


def loop(s, ts, dur):
    groups = []
    for b, t in zip(s["beats"], ts):
        if not groups or b.get("clear") or b.get("echo"):
            groups.append([])
        groups[-1].append((b, t))
    starts = [g[0][1] for g in groups]
    layers = []
    for k, g in enumerate(groups):
        items = []
        for b, t in g:
            if b.get("echo"):
                if s.get("laps"):
                    items.append(laps_row(int(s["laps"]), t + 0.05, cur=0))
                items.append(line(b, t + 0.05))
            elif b.get("url"):
                items.append(f'<div class="url fit slam" style="{d(t)}">{esc(b["text"])}</div>')
            elif b.get("text"):
                items.append(line(b, t))
        hide = f",hide .01s linear {starts[k + 1]:.2f}s forwards" if k + 1 < len(groups) else ""
        inner = (f'<div style="display:flex;flex-direction:column;gap:38px;opacity:0;animation:show .01s linear {starts[k]:.2f}s both{hide}">'
                 f'{"".join(items)}</div>')
        layers.append(inner if k == 0 else f'<div class="stage" style="z-index:4">{inner}</div>')
    return layers[0], "".join(layers[1:])


def scene_html(s, i, gid, ts, dur, start, total, spec_dir, fonts):
    t = s["type"]
    over = ""
    if t in ("hook", "text"):
        body = hook(s, ts, dur, i == 0)
    elif t == "triangle":
        body = triangle(s, ts, dur)
    elif t == "reveal":
        body = reveal(s, ts, dur)
        over = f'<div class="flash" style="{d(ts[0])}"></div>'
    elif t == "loop":
        body, over = loop(s, ts, dur)
    else:
        raise SystemExit(f"Scene type '{t}' is not in the race theme (hook, text, triangle, reveal, loop)")
    ghost = esc(s.get("ghost", ""))
    return (f'<!doctype html><html><head><meta charset="utf-8">{fonts}{_anton_link()}<style>{CSS}</style></head><body>'
            f'<div class="reel" style="--dur:{dur:.2f}s"><div class="streaks"></div><div class="ghost">{ghost}</div>'
            f'<div class="band b2"></div><div class="band b1"></div><div class="band b3"></div>'
            f'<div class="stage{" tight" if t == "triangle" else ""}">{body}</div>{over}</div></body></html>')


def _anton_link():
    from common import CACHE
    css = CACHE / "fonts" / "node_modules" / "@fontsource" / "anton" / "400.css"
    if not css.exists():
        raise SystemExit(f"Missing font {css}. Run automation/scripts/setup.sh first.")
    return f'<link rel="stylesheet" href="file://{css}">'
