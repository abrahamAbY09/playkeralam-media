"""The "studio" reel look (added 21 Nov 2026 for the B style rules): a dark TV quiz-show stage with swaying
spotlights, the game's REAL screen shown large, huge bold English lines, and all text inside Meta's Reels
safe zone (y 270-1250, x 65-960 on 1080x1920). No sunburst, no dots, no cream cards, no badge or CTA pills.

Use it with "theme": "studio" in a reel spec. render_reel.py calls scene_html() below for every scene.

Scene types in this theme (per-beat fields in [ ]):
  hook / text  [say, text, style: big|mid|gold]        kinetic lines, push-in; the first is on screen at frame 0
  quiz         crop [x,y,w,h] (px in the shot)        the real game screen, large, one question per beat:
               [say, text, shot, count, qn, reply]     caption = text, counter = count ("films left"), a ticking
                                                       bar runs on the panel, a YES/NO stamp lands mid-line
  reveal       shot, crop  [say, text, style]          white flash, the real result screen, a gold sweep
  loop         [say, text, url?, echo?]                share trigger + playkeralam.com; an "echo" beat clears the
                                                       stage and shows the hook's first line again so a replay
                                                       flows straight back into the opening
Palette: night teal #071419 → #1F5F74, spotlight gold #F2B33D, warm white #FFF7E6, yes green #2FBF71.
"""
import json
import pathlib

from PIL import Image

from common import esc as _esc

NIGHT, TEAL, GOLD, WHITE, YES, NO = "#071419", "#1F5F74", "#F2B33D", "#FFF7E6", "#2FBF71", "#E0533D"
SAFE = dict(top=270, bottom=1250, left=65, right=960)  # Meta Reels safe area on 1080x1920
PAD = 10   # the stage sits this far inside SAFE so the 2% push-in never crosses the safe lines
STAGE_W = SAFE['right'] - SAFE['left'] - 2 * PAD

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:{NIGHT}}}
body{{font-family:'Baloo Chettan 2',sans-serif;color:{WHITE};-webkit-font-smoothing:antialiased}}
.reel{{position:relative;width:1080px;height:1920px;overflow:hidden;
  background:radial-gradient(120% 70% at 50% 28%,{TEAL} 0%,#0E2E3A 45%,{NIGHT} 80%)}}
.ghost{{position:absolute;inset:-120px;background-size:cover;background-position:center top;filter:blur(26px) brightness(.32) saturate(1.3);
  animation:drift var(--dur) linear both}}
@keyframes drift{{from{{transform:scale(1.18) translateY(30px)}}to{{transform:scale(1.28) translateY(-40px)}}}}
.beam{{position:absolute;top:-260px;width:1000px;height:2500px;transform-origin:50% 0;filter:blur(14px);
  background:linear-gradient(to bottom,rgba(255,214,140,.42),rgba(255,214,140,.10) 55%,transparent 80%);
  clip-path:polygon(44% 0,56% 0,100% 100%,0 100%);mix-blend-mode:screen}}
.beam.a{{left:-420px;animation:swayA 2.6s ease-in-out infinite alternate}}
.beam.b{{right:-420px;animation:swayB 3.1s ease-in-out infinite alternate}}
@keyframes swayA{{from{{transform:rotate(-24deg)}}to{{transform:rotate(-8deg)}}}}
@keyframes swayB{{from{{transform:rotate(22deg)}}to{{transform:rotate(6deg)}}}}
.floor{{position:absolute;left:-40%;right:-40%;bottom:-40px;height:1250px;transform:perspective(1100px) rotateX(52deg);transform-origin:50% 100%;
  background:radial-gradient(50% 60% at 50% 35%,rgba(242,179,61,.6),rgba(242,179,61,.18) 60%,rgba(242,179,61,.05) 90%),
  repeating-linear-gradient(90deg,rgba(242,179,61,.55) 0 5px,transparent 5px 140px),
  repeating-linear-gradient(0deg,rgba(242,179,61,.45) 0 5px,transparent 5px 140px);
  animation:roll 1.2s linear infinite}}
@keyframes roll{{from{{background-position:0 0,0 0,0 0}}to{{background-position:0 0,0 0,0 140px}}}}
.qm{{position:absolute;right:-60px;bottom:330px;font-weight:800;font-size:1100px;line-height:1;color:transparent;
  -webkit-text-stroke:10px rgba(242,179,61,.28);animation:qm var(--dur) linear both}}
@keyframes qm{{from{{transform:rotate(8deg) scale(1)}}to{{transform:rotate(-4deg) scale(1.08)}}}}
.vig{{position:absolute;inset:0;background:radial-gradient(90% 60% at 50% 40%,transparent 55%,rgba(0,0,0,.55))}}
.stage{{position:absolute;left:{SAFE['left'] + PAD}px;top:{SAFE['top'] + PAD}px;width:{STAGE_W}px;
  height:{SAFE['bottom'] - SAFE['top'] - 2 * PAD}px;display:flex;flex-direction:column;justify-content:center;gap:30px;z-index:3;
  animation:push var(--dur) linear both;transform-origin:50% 45%}}
.stage>*{{flex:none}}
@keyframes push{{from{{transform:scale(1)}}to{{transform:scale(1.02)}}}}
.line{{font-weight:800;line-height:1.0;letter-spacing:-1px;text-shadow:0 10px 34px rgba(0,0,0,.55);white-space:normal}}
.big{{font-size:124px}} .mid{{font-size:108px}} .gold{{color:{GOLD}}}
.rise{{opacity:0;animation:rise .34s cubic-bezier(.2,1.2,.4,1) var(--d,0s) both}}
@keyframes rise{{0%{{opacity:0;transform:translateY(90px) scale(.92);filter:blur(10px)}}100%{{opacity:1;transform:none;filter:none}}}}
.slam{{opacity:0;animation:slam .3s cubic-bezier(.2,1.1,.4,1) var(--d,0s) both}}
@keyframes slam{{0%{{opacity:0;transform:scale(1.8) rotate(var(--r,0deg))}}60%{{opacity:1;transform:scale(.95) rotate(var(--r,0deg))}}100%{{opacity:1;transform:scale(1) rotate(var(--r,0deg))}}}}
.out{{animation:out .18s ease-in var(--o) forwards}}
@keyframes out{{to{{opacity:0;transform:translateY(-40px)}}}}
.hl{{background:linear-gradient({GOLD},{GOLD}) no-repeat 0 88%/0% 22%;animation:sweep .45s ease-out var(--d,0s) forwards;padding:0 6px}}
@keyframes sweep{{to{{background-size:100% 22%}}}}
.dark{{color:{NIGHT};text-shadow:none}}
/* quiz */
.top{{display:flex;align-items:flex-end;justify-content:space-between;height:150px;position:relative}}
.qn{{font-weight:800;font-size:64px;color:{NIGHT};background:{GOLD};border-radius:20px;padding:12px 26px 2px;position:absolute;left:0;bottom:12px}}
.cnt{{position:absolute;right:0;bottom:0;text-align:right}}
.cnt b{{display:block;font-weight:800;font-size:128px;line-height:.9;color:{GOLD};text-shadow:0 0 40px rgba(242,179,61,.5)}}
.cnt span{{font-weight:600;font-size:40px;opacity:.85}}
.slot{{position:relative}}
.slot>*{{position:absolute;inset:0}}
.panel{{position:relative;width:100%;border-radius:30px;overflow:hidden;background-repeat:no-repeat;
  box-shadow:0 0 0 5px {GOLD},0 30px 80px rgba(0,0,0,.6),0 0 90px rgba(242,179,61,.35)}}
.tick{{position:absolute;left:0;bottom:0;height:16px;background:{GOLD};width:0;animation:fill var(--len) linear var(--d) both}}
@keyframes fill{{to{{width:100%}}}}
.stamp{{position:absolute;right:30px;top:40%;font-weight:800;font-size:118px;line-height:1;padding:26px 40px 8px;border-radius:26px;
  color:#fff;border:8px solid #fff;--r:-12deg;box-shadow:0 18px 50px rgba(0,0,0,.5)}}
.stamp.yes{{background:{YES}}} .stamp.no{{background:{NO}}}
.cap{{font-weight:800;font-size:100px;line-height:1.0;text-shadow:0 10px 34px rgba(0,0,0,.6)}}
.flash{{position:absolute;inset:0;background:#fff;z-index:9;animation:flash .32s ease-out var(--d,0s) both;opacity:0}}
@keyframes flash{{from{{opacity:.95}}to{{opacity:0}}}}
.url{{font-weight:800;font-size:112px;color:{GOLD};letter-spacing:-2px}}
"""


def esc(t):
    return _esc(str(t or "").replace("‌", ""))


def d(t):
    return f"--d:{t:.2f}s"


def crop_style(shot_path, crop, width):
    """Background CSS that shows only crop [x, y, w, h] of the shot, scaled to `width` px wide."""
    im = Image.open(shot_path)
    x, y, w, h = crop
    s = width / w
    return (f"background-image:url('file://{shot_path}');background-size:{im.width * s:.0f}px {im.height * s:.0f}px;"
            f"background-position:{-x * s:.0f}px {-y * s:.0f}px;height:{h * s:.0f}px"), h * s


def ends(ts, dur):
    return [ts[k + 1] if k + 1 < len(ts) else dur + 5 for k in range(len(ts))]


def hook(s, ts, dur, first):
    out = []
    for i, (b, t) in enumerate(zip(s["beats"], ts)):
        if not b.get("text"):
            continue
        if first and i == 0 and t == 0:
            t = -0.4  # fully landed on frame 0: the hook is the first thing anyone sees
        cls = {"mid": "mid", "gold": "big gold"}.get(b.get("style"), "big")
        out.append(f'<div class="line {cls} fit rise" style="{d(t)}">{esc(b["text"])}</div>')
    return "".join(out)


def quiz(s, ts, dur, spec_dir):
    width = STAGE_W
    en = ends(ts, dur)
    panels, caps, cnts, qns = [], [], [], []
    ph = 0
    for k, (b, t) in enumerate(zip(s["beats"], ts)):
        shot = (spec_dir / b.get("shot", s.get("shot"))).resolve()
        st, ph = crop_style(shot, b.get("crop", s["crop"]), width)
        last = k == len(ts) - 1
        vis = f"opacity:0;animation:show .01s linear {t:.2f}s forwards" + ("" if last else f",hide .01s linear {en[k]:.2f}s forwards")
        reply = b.get("reply", "")
        stamp = (f'<div class="stamp slam {"no" if reply.upper() == "NO" else "yes"}" style="{d(t + float(b.get("stampAt", 0.62 * ((en[k] if not last else dur) - t))))}">{esc(reply)}</div>'
                 if reply else "")
        panels.append(f'<div style="{vis}"><div class="panel" style="{st};transform:perspective(1400px) rotateX(5deg)">'
                      f'<div class="tick" style="{d(t)};--len:{max(0.3, en[k] - t if not last else dur - t):.2f}s"></div>{stamp}</div></div>')
        caps.append(f'<div style="{vis}"><div class="cap fit rise" style="{d(t)}">{esc(b.get("text"))}</div></div>')
        cnts.append(f'<div style="{vis}"><div class="cnt slam" style="{d(t)}"><b>{esc(b.get("count", ""))}</b><span>{esc(s.get("countLabel", "films left"))}</span></div></div>')
        if b.get("qn"):
            qns.append(f'<div style="{vis}"><div class="qn slam" style="{d(t)};--r:-4deg">{esc(b.get("qn", ""))}</div></div>')
    return (f'<div class="top"><div class="slot" style="height:150px;width:100%">{"".join(qns)}{"".join(cnts)}</div></div>'
            f'<div class="slot" style="height:{ph:.0f}px">{"".join(panels)}</div>'
            f'<div class="slot" style="height:210px">{"".join(caps)}</div>')


def reveal(s, ts, dur, spec_dir):
    shot = (spec_dir / s["shot"]).resolve()
    st, ph = crop_style(shot, s["crop"], STAGE_W)
    out = [f'<div class="panel rise" style="{st};{d(ts[0])}"></div>']
    for i, (b, t) in enumerate(zip(s["beats"], ts)):
        if not b.get("text"):
            continue
        cls = {"title": "big gold", "mid": "mid"}.get(b.get("style"), "mid")
        hl = ' hl' if b.get("sweep") else ""
        inner = f'<span class="{hl.strip()}" style="{d(t + 0.25)}">{esc(b["text"])}</span>' if hl else esc(b["text"])
        out.append(f'<div class="line {cls} fit slam" style="{d(t)};--r:{-2 if i == 0 else 1}deg">{inner}</div>')
    return "".join(out), f'<div class="flash" style="{d(ts[0])}"></div>'


def loop(s, ts, dur):
    """Beats stack up in a group; a beat with "clear": true (or "echo": true) starts a fresh group, so no
    frame carries more than one idea. The echo group repeats the hook's first line for a seamless replay."""
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
            if not b.get("text"):
                continue
            if b.get("url"):
                items.append(f'<div class="url fit slam" style="{d(t)}">{esc(b["text"])}</div>')
            elif b.get("echo"):
                items.append(f'<div class="line big fit rise" style="{d(t + 0.1)}">{esc(b["text"])}</div>')
                if b.get("ghostLine"):  # the hook's 2nd line, invisible, so the echo sits where the hook did
                    items.append(f'<div class="line big gold" style="visibility:hidden">{esc(b["ghostLine"])}</div>')
            else:
                cls = "big gold" if b.get("style") == "gold" else "mid"
                items.append(f'<div class="line {cls} fit rise" style="{d(t)}">{esc(b["text"])}</div>')
        hide = f",hide .01s linear {starts[k + 1]:.2f}s forwards" if k + 1 < len(groups) else ""
        z = ' style="z-index:4"' if k else ""
        layers.append(f'<div class="{"stage" if k else "grp"}"{z}>'
                      f'<div style="display:flex;flex-direction:column;gap:30px;animation:show .01s linear {starts[k]:.2f}s both{hide};opacity:0">'
                      f'{"".join(items)}</div></div>')
    return layers[0], "".join(layers[1:])


def scene_html(s, i, gid, ts, dur, start, total, spec_dir, fonts):
    t = s["type"]
    over, ghost = "", ""
    if t in ("hook", "text"):
        body = hook(s, ts, dur, i == 0)
    elif t == "quiz":
        body = quiz(s, ts, dur, spec_dir)
        first = (spec_dir / (s["beats"][0].get("shot") or s.get("shot"))).resolve()
        ghost = f'<div class="ghost" style="background-image:url(\'file://{first}\')"></div>'
    elif t == "reveal":
        body, over = reveal(s, ts, dur, spec_dir)
        ghost = f'<div class="ghost" style="background-image:url(\'file://{(spec_dir / s["shot"]).resolve()}\')"></div>'
    elif t == "loop":
        body, over = loop(s, ts, dur)
    else:
        raise SystemExit(f"Scene type '{t}' is not in the studio theme (hook, text, quiz, reveal, loop)")
    if t in ("hook", "text", "loop"):
        ghost = '<div class="qm">?</div>'
    extra = "@keyframes show{to{opacity:1}}@keyframes hide{to{opacity:0;visibility:hidden}}"
    return (f'<!doctype html><html><head><meta charset="utf-8">{fonts}<style>{CSS}{extra}</style></head><body>'
            f'<div class="reel" style="--dur:{dur:.2f}s">{ghost}<div class="beam a"></div><div class="beam b"></div>'
            f'<div class="floor"></div><div class="vig"></div>'
            f'<div class="stage">{body}</div>{over}</div></body></html>')
