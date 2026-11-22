"""The "board" reel look (added 22 Nov 2026 for the B style rules): a crisp editorial puzzle page. Warm newsprint
paper with a faint crossword grid drifting behind, ink-black serif headlines (DM Serif Display, Baloo Chettan 2
for Malayalam), a yellow highlighter sweep, the game's tiles shown HUGE and flipping like the real board, and a
deep green ink slab bleeding off the bottom. Made for word, film and trivia puzzles (Vaakku, Paryayam, Thaaranira,
Katha, Aadyam). All text sits inside Meta's Reels safe zone (y 270-1250, x 65-960). No sunburst, dots, cream
cards, badge pill, CTA pill or floating phone.

Use it with "theme": "board" in a reel spec. render_reel.py calls scene_html() below for every scene.

Scene types (scene fields; per-beat fields in [ ]):
  hook / text  tiles? [say, text, style: serif|mark|kick, showTiles]   lines stamp in; the first is on screen at
               frame 0. "tiles" (list of {text, color: green|yellow|grey|blank}) appears with the beat that
               has "showTiles": true.
  board        kicker, tiles  [say, text, timer, sfx, dur]   the tiles fill the frame; one caption per beat
               (each replaces the last); a beat with "timer": true starts a ticking bar on the board that runs
               to the end of the scene (add silent "dur" beats with "sfx": "tick" for the thinking window).
  reveal       tiles (final), word, sense  [say, text]       the tiles flip to their final colours one by one,
               the word stamps in with its English sense highlighted; later beats add one line each.
  loop         tiles?  [say, text, url, echo, clear]         share trigger + playkeralam.com; an "echo" beat
               clears the page and brings back the hook's first line over blank tiles, so a replay flows on.
Palette: paper #F1ECDF, ink #141414, Vaakku green #2E8B57 / #1E6B43, highlighter #F6C945, grey #8C877B.
"""
from common import esc as _esc

PAPER, INK, GREEN, DEEP, HI, GREY, YEL = "#F1ECDF", "#141414", "#2E8B57", "#1E6B43", "#F6C945", "#8C877B", "#D9A520"
SAFE = dict(top=270, bottom=1250, left=65, right=960)
PAD = 12
STAGE_W = SAFE['right'] - SAFE['left'] - 2 * PAD

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:{PAPER}}}
body{{font-family:'Baloo Chettan 2',sans-serif;color:{INK};-webkit-font-smoothing:antialiased}}
.reel{{position:relative;width:1080px;height:1920px;overflow:hidden;background:{PAPER}}}
.grain{{position:absolute;inset:0;background:radial-gradient(120% 80% at 30% 20%,rgba(255,255,255,.7),transparent 60%),
  radial-gradient(90% 70% at 80% 90%,rgba(120,100,60,.16),transparent 70%)}}
.grid{{position:absolute;left:-200px;top:-200px;width:1600px;height:2400px;
  background-image:linear-gradient(rgba(20,20,20,.075) 3px,transparent 3px),linear-gradient(90deg,rgba(20,20,20,.075) 3px,transparent 3px);
  background-size:170px 170px;animation:gdrift var(--dur) linear both}}
@keyframes gdrift{{from{{transform:translate(0,0) rotate(-4deg)}}to{{transform:translate(-60px,-110px) rotate(-4deg)}}}}
.ghostL{{position:absolute;right:-90px;top:120px;font-family:'Baloo Chettan 2';font-weight:800;font-size:900px;line-height:1;color:rgba(30,107,67,.07);
  animation:gl var(--dur) linear both}}
@keyframes gl{{from{{transform:translateY(40px) rotate(6deg)}}to{{transform:translateY(-60px) rotate(2deg)}}}}
.rule{{position:absolute;left:0;right:0;top:222px;height:30px;border-top:6px solid {INK};border-bottom:2px solid {INK};
  transform-origin:0 50%;animation:ruleIn .5s cubic-bezier(.2,1,.3,1) both}}
@keyframes ruleIn{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
.slab{{position:absolute;left:-40px;right:-40px;bottom:-40px;height:720px;background:{DEEP};
  clip-path:polygon(0 18%,100% 6%,100% 100%,0 100%);animation:slab var(--dur) linear both}}
.slab::after{{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.07) 3px,transparent 3px),
  linear-gradient(90deg,rgba(255,255,255,.07) 3px,transparent 3px);background-size:170px 170px}}
@keyframes slab{{from{{transform:translateY(30px)}}to{{transform:translateY(0)}}}}
.stage{{position:absolute;left:{SAFE['left'] + PAD}px;top:{SAFE['top'] + PAD}px;width:{STAGE_W}px;
  height:{SAFE['bottom'] - SAFE['top'] - 2 * PAD}px;display:flex;flex-direction:column;justify-content:center;gap:44px;z-index:3;
  animation:push var(--dur) linear both;transform-origin:50% 50%}}
.stage>*{{flex:none}}
@keyframes push{{from{{transform:scale(1)}}to{{transform:scale(1.025)}}}}
.serif{{font-family:'DM Serif Display','Baloo Chettan 2',serif;font-weight:400;font-size:150px;line-height:.98;letter-spacing:-2px;color:{INK}}}
.serif.sm{{font-size:116px}}
.kick{{font-weight:800;font-size:48px;letter-spacing:8px;color:{DEEP};text-transform:uppercase;border-bottom:5px solid {INK};padding-bottom:4px;align-self:flex-start}}
.mk{{background:linear-gradient({HI},{HI}) no-repeat 0 82%/0% 44%;animation:sweep .42s ease-out var(--d,0s) forwards;padding:0 8px;margin:0 -8px}}
@keyframes sweep{{to{{background-size:100% 44%}}}}
.stamp{{opacity:0;animation:stamp .32s cubic-bezier(.2,1.2,.35,1) var(--d,0s) both}}
@keyframes stamp{{0%{{opacity:0;transform:translateY(-30px) scale(1.25);filter:blur(6px)}}100%{{opacity:1;transform:none;filter:none}}}}
.rise{{opacity:0;animation:rise .3s cubic-bezier(.2,1.1,.4,1) var(--d,0s) both}}
@keyframes rise{{0%{{opacity:0;transform:translateY(70px)}}100%{{opacity:1;transform:none}}}}
@keyframes show{{to{{opacity:1}}}}
@keyframes hide{{to{{opacity:0;visibility:hidden}}}}
.tiles{{display:flex;justify-content:center;gap:30px;perspective:1200px}}
.tl{{width:270px;height:270px;border:9px solid {INK};border-radius:22px;background:#FBF8F0;display:flex;align-items:center;justify-content:center;
  font-weight:800;font-size:132px;padding-top:26px;color:{INK};box-shadow:0 14px 0 rgba(20,20,20,.18);
  opacity:0;animation:flipIn .36s cubic-bezier(.2,1.1,.4,1) var(--d,0s) both}}
.tiles.md .tl{{width:230px;height:230px;font-size:112px;padding-top:22px}}
@keyframes flipIn{{0%{{opacity:0;transform:rotateX(90deg)}}100%{{opacity:1;transform:rotateX(0)}}}}
.tl.blank::after{{content:"?";font-family:'DM Serif Display',serif;font-size:120px;color:rgba(20,20,20,.16);padding-bottom:22px;animation:qp .8s ease-in-out infinite alternate}}
@keyframes qp{{from{{opacity:.5}}to{{opacity:1}}}}
.tl.green{{background:{GREEN};border-color:{DEEP};color:#fff}}
.tl.yellow{{background:{YEL};border-color:#A27A10;color:#fff}}
.tl.grey{{background:{GREY};border-color:#615D53;color:#fff}}
.tl.turn{{animation:flipIn .36s cubic-bezier(.2,1.1,.4,1) var(--d0,0s) both,turn .5s ease-in-out var(--d,0s) both}}
@keyframes turn{{0%{{transform:rotateX(0);color:transparent}}50%{{transform:rotateX(90deg);background:#FBF8F0;border-color:{INK};color:transparent}}
  51%{{transform:rotateX(90deg);background:{GREEN};border-color:{DEEP};color:#fff}}100%{{transform:rotateX(0);background:{GREEN};border-color:{DEEP};color:#fff}}}}
.timer{{position:relative;height:34px;border:6px solid {INK};border-radius:20px;overflow:hidden;background:#FBF8F0;margin:0 4px}}
.timer i{{position:absolute;left:0;top:0;bottom:0;width:0;background:{GREEN};animation:fill var(--len) linear var(--d) both,warn var(--len) steps(1) var(--d) both}}
@keyframes fill{{to{{width:100%}}}}
@keyframes warn{{0%,65%{{background:{GREEN}}}66%,100%{{background:#D0452F}}}}
.timer.idle i{{animation:none}}
.slot{{position:relative}}
.slot>*{{position:absolute;left:0;right:0;top:0}}
.cap{{font-family:'DM Serif Display','Baloo Chettan 2',serif;font-size:108px;line-height:1.0;letter-spacing:-1px}}
.cap .ml{{font-family:'Baloo Chettan 2';font-weight:800;color:{DEEP}}}
.sense{{font-family:'DM Serif Display',serif;font-size:100px;line-height:1}}
.url{{font-family:'DM Serif Display',serif;font-size:124px;letter-spacing:-2px;color:{DEEP}}}
.wipe{{position:absolute;inset:0;background:{GREEN};z-index:9;transform-origin:0 50%;animation:wipe .34s ease-in var(--d,0s) both;opacity:0}}
@keyframes wipe{{0%{{opacity:1;transform:scaleX(0)}}55%{{opacity:1;transform:scaleX(1)}}100%{{opacity:0;transform:scaleX(1)}}}}
"""


def esc(t):
    return _esc(str(t or "").replace("‌", ""))


def d(t):
    return f"--d:{t:.2f}s"


def ends(ts, dur):
    return [ts[k + 1] if k + 1 < len(ts) else dur + 5 for k in range(len(ts))]


def vis(t, end, last):
    return f"opacity:0;animation:show .01s linear {t:.2f}s forwards" + ("" if last else f",hide .01s linear {end:.2f}s forwards")


def rich(text):
    """`*word*` gets the highlighter; Malayalam runs get the Malayalam face in green."""
    import re
    out = esc(text)
    out = re.sub(r"\*(.+?)\*", r'<span class="mk" style="--d:VAR">\1</span>', out)
    out = re.sub(r"([ഀ-ൿ]+)", r'<span class="ml">\1</span>', out)
    return out


def tiles_row(tiles, t0, step=0.08, cls="", turn_at=None):
    cells = []
    for i, tl in enumerate(tiles):
        col = tl.get("color", "blank")
        if turn_at is not None:  # start blank-looking, flip to green with its letter
            first = tl.get("from") == "green"
            c = "tl green" if first else "tl turn"
            st = f"--d0:{t0 + i * step:.2f}s;--d:{turn_at + i * 0.12:.2f}s" if not first else d(t0 + i * step)
            cells.append(f'<div class="{c}" style="{st}">{esc(tl.get("text", ""))}</div>')
        else:
            cells.append(f'<div class="tl {col}" style="{d(t0 + i * step)}">{esc(tl.get("text", "") if col != "blank" else "")}</div>')
    return f'<div class="tiles {cls}">{"".join(cells)}</div>'


def line(b, t):
    style = b.get("style", "serif")
    txt = rich(b["text"]).replace("VAR", f"{t + 0.22:.2f}s")
    if style == "kick":
        return f'<div class="kick stamp" style="{d(t)}">{txt}</div>'
    cls = "serif sm" if style == "sm" else "serif"
    return f'<div class="{cls} fit stamp" style="{d(t)}">{txt}</div>'


def hook(s, ts, dur, first):
    out = []
    for i, (b, t) in enumerate(zip(s["beats"], ts)):
        if first and i == 0 and t == 0:
            t = -0.4  # fully landed on frame 0
        if b.get("text"):
            out.append(line(b, t))
        if b.get("showTiles") and s.get("tiles"):
            out.append(tiles_row(s["tiles"], t + 0.05, cls="md"))
    return "".join(out)


def board(s, ts, dur):
    en = ends(ts, dur)
    kick = f'<div class="kick stamp" style="{d(ts[0])}">{esc(s["kicker"])}</div>' if s.get("kicker") else ""
    tiles = tiles_row(s["tiles"], ts[0], step=0.1)
    tstart = next((t for b, t in zip(s["beats"], ts) if b.get("timer")), None)
    if tstart is None:
        timer = '<div class="timer idle"><i></i></div>'
    else:
        timer = f'<div class="timer"><i style="{d(tstart)};--len:{max(0.5, dur - tstart - 0.1):.2f}s"></i></div>'
    caps = []
    texted = [(k, b, t) for k, (b, t) in enumerate(zip(s["beats"], ts)) if b.get("text")]
    for j, (k, b, t) in enumerate(texted):
        end = texted[j + 1][2] if j + 1 < len(texted) else dur + 5
        caps.append(f'<div style="{vis(t, end, j == len(texted) - 1)}"><div class="cap fit stamp" style="{d(t)}">'
                    f'{rich(b["text"]).replace("VAR", f"{t + 0.22:.2f}s")}</div></div>')
    return f'{kick}{tiles}{timer}<div class="slot" style="height:250px">{"".join(caps)}</div>'


def reveal(s, ts, dur):
    t0 = ts[0]
    tiles = tiles_row(s["tiles"], -0.4, turn_at=t0 + 0.22, step=0)
    word = f'<div class="serif fit stamp" style="{d(t0 + 0.3)};text-align:center">{esc(s.get("word", ""))}</div>'
    sense = (f'<div class="sense stamp" style="{d(t0 + 0.42)};text-align:center"><span class="mk" style="{d(t0 + 0.6)}">'
             f'{esc(s.get("sense", ""))}</span></div>') if s.get("sense") else ""
    more = "".join(line(dict(b, style=b.get("style", "sm")), t) for b, t in list(zip(s["beats"], ts))[1:] if b.get("text"))
    return f'{tiles}{word}{sense}{more}'


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
                items.append(line(b, t + 0.05))
                if s.get("tiles"):
                    items.append(tiles_row(s["tiles"], t + 0.15, cls="md"))
            elif b.get("url"):
                items.append(f'<div class="url fit stamp" style="{d(t)}"><span class="mk" style="{d(t + 0.2)}">{esc(b["text"])}</span></div>')
            elif b.get("text"):
                items.append(line(b, t))
        hide = f",hide .01s linear {starts[k + 1]:.2f}s forwards" if k + 1 < len(groups) else ""
        inner = (f'<div style="display:flex;flex-direction:column;gap:34px;opacity:0;animation:show .01s linear {starts[k]:.2f}s both{hide}">'
                 f'{"".join(items)}</div>')
        layers.append(inner if k == 0 else f'<div class="stage" style="z-index:4">{inner}</div>')
    return layers[0], "".join(layers[1:])


def scene_html(s, i, gid, ts, dur, start, total, spec_dir, fonts):
    t = s["type"]
    over = ""
    if t in ("hook", "text"):
        body = hook(s, ts, dur, i == 0)
    elif t == "board":
        body = board(s, ts, dur)
    elif t == "reveal":
        body = reveal(s, ts, dur)
        over = f'<div class="wipe" style="{d(ts[0] - 0.12)}"></div>'
    elif t == "loop":
        body, over = loop(s, ts, dur)
    else:
        raise SystemExit(f"Scene type '{t}' is not in the board theme (hook, text, board, reveal, loop)")
    ghost = esc(s.get("ghost", ""))
    extra = ""
    return (f'<!doctype html><html><head><meta charset="utf-8">{fonts}{_serif_link()}<style>{CSS}{extra}</style></head><body>'
            f'<div class="reel" style="--dur:{dur:.2f}s"><div class="grid"></div><div class="grain"></div>'
            f'<div class="ghostL">{ghost}</div><div class="slab"></div><div class="rule"></div>'
            f'<div class="stage">{body}</div>{over}</div></body></html>')


def _serif_link():
    from common import CACHE
    css = CACHE / "fonts" / "node_modules" / "@fontsource" / "dm-serif-display" / "400.css"
    if not css.exists():
        raise SystemExit(f"Missing font {css}. Run automation/scripts/setup.sh first.")
    return f'<link rel="stylesheet" href="file://{css}">'

