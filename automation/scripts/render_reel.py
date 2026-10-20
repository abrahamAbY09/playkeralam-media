"""Render a voiced Instagram reel (1080x1920, 30 fps, H.264 + AAC) from a JSON spec.

    python3 render_reel.py spec.json OUT_DIR

Spec:
{
  "game": "thaaranira" | null,
  "voice": "arjun" | "meera" | null,     # null: by week (voice.voice_for_week of "date")
  "date": "YYYY-MM-DD",                  # the day it goes out; picks the voice and the music
  "scenes": [ {"type": ..., "say": "Malayalam script only", ...fields}, ... ]
}
Scene types (fields as in render_post.py, plus "say" for the voice-over):
  hook {title, sub, chips[]}   cast {headline, names[], hidden}   story {headline, story}
  tiles {headline, tiles[]}    pair {headline, films[], showDates, firstIndex}
  map {headline, svg, place}   answer {headline, big, details[], svg?, tiles?}
  screen {headline, shot, caption}   steps {headline, steps[]}   logos {headline, highlight[]}
  text {headline, sub}         cta {headline, sub, question}
Each scene lasts as long as its voice line plus a beat (at least "min", default 2.6 s). The whole reel
should land between config reels.minSeconds and maxSeconds. Writes reel.mp4, cover.jpg and reel.json
(duration, coverMs) into OUT_DIR, plus a contact sheet of frames to check.
"""
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (BLUE, CONFIG, CREAM, DARK, GAMES, GREEN, INK, PINK, RED, YELLOW, YELLOW2,  # noqa: E402
                    badge_uri, esc, fonts_head, game, is_dark, logo_uri, luminance, shade)
import music  # noqa: E402
from voice import speak, voice_for_week  # noqa: E402

W, H, FPS = CONFIG["reels"]["width"], CONFIG["reels"]["height"], CONFIG["reels"]["fps"]
SR = 44100
ALL_GAMES = ["vaakku", "paryayam", "thaaranira", "katha", "aadyam", "ashwamedham",
             "antakshari", "kerala-guesser", "thurupp", "cidmoosa", "sat"]

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{font-family:'Baloo Chettan 2',sans-serif;color:{INK};-webkit-font-smoothing:antialiased}}
.reel{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:var(--b1)}}
.spin{{position:absolute;left:50%;top:44%;width:3200px;height:3200px;margin:-1600px 0 0 -1600px;
  background:repeating-conic-gradient(from 0deg,var(--b1) 0deg 8deg,var(--b2) 8deg 16deg);animation:spin 40s linear infinite}}
.dots{{position:absolute;inset:0;background-color:var(--b1);background-image:radial-gradient(var(--b2) 5px,transparent 5.6px);background-size:52px 52px;animation:drift 12s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes drift{{to{{background-position:52px 104px}}}}
@keyframes pop{{0%{{transform:scale(.55) rotate(-8deg);opacity:0}}60%{{transform:scale(1.07) rotate(var(--r,0deg));opacity:1}}100%{{transform:scale(1) rotate(var(--r,0deg));opacity:1}}}}
@keyframes up{{from{{transform:translateY(120px) rotate(var(--r,0deg));opacity:0}}to{{transform:translateY(0) rotate(var(--r,0deg));opacity:1}}}}
@keyframes left{{from{{transform:translateX(-160px) rotate(var(--r,0deg));opacity:0}}to{{transform:translateX(0) rotate(var(--r,0deg));opacity:1}}}}
@keyframes right{{from{{transform:translateX(160px) rotate(var(--r,0deg));opacity:0}}to{{transform:translateX(0) rotate(var(--r,0deg));opacity:1}}}}
@keyframes bob{{0%,100%{{transform:translateY(0) rotate(var(--r,0deg))}}50%{{transform:translateY(-14px) rotate(var(--r,0deg))}}}}
@keyframes bar{{from{{width:0}}to{{width:100%}}}}
.in{{opacity:0;animation:pop .55s cubic-bezier(.2,1.3,.4,1) var(--d,0s) both}}
.up{{opacity:0;animation:up .6s cubic-bezier(.2,1.1,.4,1) var(--d,0s) both}}
.fl{{opacity:0;animation:left .55s cubic-bezier(.2,1.1,.4,1) var(--d,0s) both}}
.fr{{opacity:0;animation:right .55s cubic-bezier(.2,1.1,.4,1) var(--d,0s) both}}
.bob{{animation:bob 2.4s ease-in-out infinite}}
.head{{position:absolute;left:64px;top:110px;right:64px;display:flex;align-items:center;gap:22px;z-index:3}}
.badge{{width:120px;height:120px;border-radius:50%;border:6px solid {INK};box-shadow:7px 7px 0 {INK};background:#fff}}
.chip{{color:{INK};display:flex;align-items:center;gap:16px;background:{CREAM};border:6px solid {INK};border-radius:999px;padding:10px 34px 6px 12px;box-shadow:7px 7px 0 {INK};font-weight:800;font-size:40px;white-space:nowrap}}
.chip img{{width:70px;height:70px;border-radius:16px;margin-top:-4px}}
.stage{{position:absolute;left:64px;right:150px;top:300px;bottom:400px;display:flex;flex-direction:column;justify-content:center;gap:36px;z-index:2}}
.stage>*{{flex:none}}
.foot{{position:absolute;left:64px;bottom:300px;z-index:3;color:{INK};background:{CREAM};border:6px solid {INK};border-radius:999px;padding:12px 32px 6px;box-shadow:7px 7px 0 {INK};font-weight:800;font-size:40px}}
.progress{{position:absolute;left:0;right:0;top:0;height:16px;background:rgba(0,0,0,.25);z-index:4}}
.progress i{{display:block;height:100%;background:{YELLOW};animation:bar var(--total) linear var(--start) both}}
.h1{{font-weight:800;font-size:112px;line-height:1.18}}
.h2{{font-weight:800;font-size:80px;line-height:1.22}}
.sub{{font-family:'Manjari',sans-serif;font-weight:700;font-size:46px;line-height:1.35}}
.stroke{{-webkit-text-stroke:10px {INK};paint-order:stroke fill;text-shadow:10px 10px 0 {INK};color:var(--title)}}
.card{{color:{INK};background:{CREAM};border:8px solid {INK};border-radius:36px;box-shadow:14px 14px 0 {INK};padding:40px 46px}}
.body{{font-family:'Manjari',sans-serif;font-weight:700;font-size:48px;line-height:1.42}}
.biglogo{{width:300px;height:300px;border-radius:68px;border:8px solid {INK};box-shadow:16px 16px 0 {INK};background:#fff;--r:-6deg}}
.chips{{display:flex;flex-wrap:wrap;gap:18px}}
.chips span{{color:{INK};background:{YELLOW};border:6px solid {INK};border-radius:999px;padding:12px 30px 6px;font-weight:800;font-size:40px;box-shadow:6px 6px 0 {INK}}}
.chips span:nth-child(2n){{background:{PINK}}}
.names{{display:flex;flex-direction:column;gap:22px}}
.name{{color:{INK};display:flex;align-items:center;gap:26px;background:{CREAM};border:7px solid {INK};border-radius:28px;box-shadow:9px 9px 0 {INK};padding:22px 32px 12px;font-weight:800;font-size:60px}}
.name .k{{flex:none;width:82px;height:82px;border-radius:50%;background:{YELLOW};border:6px solid {INK};display:flex;align-items:center;justify-content:center;font-size:46px;padding-top:6px}}
.name.hid{{background:{INK};color:{YELLOW2};letter-spacing:10px}}
.tiles{{display:flex;flex-wrap:wrap;gap:22px;justify-content:center}}
.tile{{min-width:190px;height:190px;padding:24px 24px 0;border:8px solid {INK};border-radius:30px;box-shadow:10px 10px 0 {INK};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:96px;color:#fff}}
.t-green{{background:{GREEN}}} .t-yellow{{background:{YELLOW};color:{INK}}} .t-grey{{background:#9A958A}} .t-blue{{background:{BLUE}}}
.t-cream{{background:{CREAM};color:{INK}}} .t-blank{{background:{CREAM};color:{INK};border-style:dashed}}
.film{{color:{INK};position:relative;background:{CREAM};border:8px solid {INK};border-radius:34px;box-shadow:12px 12px 0 {INK};padding:34px 40px 28px 160px}}
.film .ab{{color:{INK};position:absolute;left:34px;top:50%;margin-top:-52px;width:104px;height:104px;border-radius:50%;background:{YELLOW};border:7px solid {INK};font-weight:800;font-size:60px;display:flex;align-items:center;justify-content:center;padding-top:8px}}
.film .ti{{font-weight:800;font-size:66px;line-height:1.1}}
.film .me{{font-family:'Manjari',sans-serif;font-weight:700;font-size:36px;line-height:1.35;margin-top:6px}}
.film .dt{{display:inline-block;margin-top:14px;background:{INK};color:{YELLOW};border-radius:16px;padding:10px 20px 4px;font-weight:800;font-size:40px}}
.film.win{{background:{GREEN};color:#fff}} .film.win .ab{{background:{CREAM}}}
.mapbox svg{{height:900px;width:auto;border-radius:20px;filter:drop-shadow(12px 12px 0 {INK})}}
.answer .mapbox svg{{height:760px}}
.phone{{position:relative;width:390px;height:845px;border-radius:72px;border:18px solid {INK};box-shadow:18px 18px 0 {INK};overflow:hidden;background:#000;--r:3deg}}
.phone img{{width:100%;height:100%;object-fit:cover;object-position:top}}
.steps{{display:flex;flex-direction:column;gap:30px}}
.step{{display:flex;gap:30px;align-items:center}}
.step .n{{color:{INK};flex:none;width:120px;height:120px;border-radius:50%;border:7px solid {INK};background:{YELLOW};box-shadow:8px 8px 0 {INK};font-weight:800;font-size:70px;display:flex;align-items:center;justify-content:center;padding-top:10px}}
.step .t{{font-weight:800;font-size:56px;line-height:1.15}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:30px 26px}}
.gi{{display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;font-weight:800;font-size:34px;line-height:1.1}}
.gi img{{width:180px;height:180px;border-radius:42px;border:7px solid {INK};box-shadow:9px 9px 0 {INK};background:#fff}}
.url-big{{color:{INK};background:{YELLOW};border:9px solid {INK};border-radius:999px;box-shadow:16px 16px 0 {INK};padding:34px 24px 22px;text-align:center;font-weight:800;font-size:82px;--r:1.5deg}}
.tag{{align-self:center;background:{RED};color:{CREAM};border:7px solid {INK};border-radius:18px;padding:14px 34px 8px;font-weight:800;font-size:44px;--r:-3deg;margin-top:-34px}}
.q{{align-self:flex-start;background:{PINK};color:{INK};border:7px solid {INK};border-radius:22px;padding:18px 32px 10px;font-weight:800;font-size:44px;line-height:1.25;--r:-1.5deg}}
"""


def tiles_html(tiles, base_delay=0.3, step=0.18):
    return '<div class="tiles">' + "".join(
        f'<div class="tile in t-{esc(t.get("color", "cream"))}" style="--d:{base_delay + i * step:.2f}s">{esc(t.get("text", ""))}</div>'
        for i, t in enumerate(tiles)) + "</div>"


def scene_body(s, gid, dur):
    t = s["type"]
    hl = f'<div class="h2 up" style="--d:.05s">{esc(s.get("headline"))}</div>' if s.get("headline") else ""
    if t == "hook":
        logo = logo_uri(game(gid)["logo"]) if gid else badge_uri()
        chips = "".join(f'<span class="in" style="--d:{0.9 + i * 0.15:.2f}s">{esc(c)}</span>' for i, c in enumerate(s.get("chips", [])))
        return (f'<img class="biglogo in" style="--d:.1s" src="{logo}">'
                f'<div class="h1 stroke in" style="--d:.35s">{esc(s.get("title"))}</div>'
                f'<div class="sub up" style="--d:.6s">{esc(s.get("sub"))}</div><div class="chips">{chips}</div>')
    if t == "cast":
        names = s["names"]
        step = min(1.3, max(0.5, (dur - 1.2) / max(1, len(names))))
        rows = "".join(f'<div class="name fl" style="--d:{0.5 + i * step:.2f}s"><div class="k">{i + 1}</div>{esc(n)}</div>' for i, n in enumerate(names))
        rows += "".join(f'<div class="name hid fl" style="--d:{0.5 + (len(names) + j) * step * 0.5:.2f}s"><div class="k" style="color:{INK};letter-spacing:0">{len(names) + j + 1}</div>? ? ? ? ?</div>'
                        for j in range(int(s.get("hidden", 0))))
        return f'{hl}<div class="names">{rows}</div>'
    if t == "story":
        return f'{hl}<div class="card up" style="--d:.4s;--r:1deg"><div class="body">{esc(s["story"])}</div></div>'
    if t == "tiles":
        return f'{hl}{tiles_html(s["tiles"])}'
    if t == "pair":
        films = []
        for i, f in enumerate(s["films"]):
            win = " win" if s.get("firstIndex") == i else ""
            date = f'<div class="dt">{esc(f.get("date"))}</div>' if s.get("showDates") and f.get("date") else ""
            meta = " · ".join(x for x in [f.get("director"), ", ".join(f.get("cast", [])[:3])] if x)
            films.append(f'<div class="film{win} {"fl" if i == 0 else "fr"}" style="--d:{0.4 + i * 0.5:.2f}s"><div class="ab">{"AB"[i]}</div>'
                         f'<div class="ti">{esc(f["title"])}</div><div class="me">{esc(meta)}</div>{date}</div>')
        return f'{hl}<div style="display:flex;flex-direction:column;gap:34px">{"".join(films)}</div>'
    if t == "map":
        place = f'<div class="card in" style="--d:.3s;--r:-2deg;padding:26px 36px"><div class="h2">{esc(s.get("place"))}</div></div>' if s.get("place") else ""
        return f'{hl}{place}<div class="mapbox up" style="--d:.6s">{s["svg"]}</div>'
    if t == "answer":
        extra = ""
        if s.get("svg"):
            extra = f'<div class="mapbox up" style="--d:.7s">{s["svg"]}</div>'
        elif s.get("tiles"):
            extra = tiles_html(s["tiles"], 0.6)
        details = "".join(f"<div>{esc(d)}</div>" for d in s.get("details", []))
        det = f'<div class="card up" style="--d:.9s"><div class="body" style="font-size:42px">{details}</div></div>' if details else ""
        return (f'<div class="answer" style="display:flex;flex-direction:column;gap:34px">{hl}'
                f'<div class="h1 stroke in" style="--d:.3s">{esc(s.get("big"))}</div>{extra}{det}</div>')
    if t == "screen":
        shot = (SPEC_DIR / s["shot"]).resolve()
        if not shot.exists():
            raise SystemExit(f"Missing screenshot {shot}")
        cap = f'<div class="card up" style="--d:.9s;padding:24px 34px"><div class="body" style="font-size:42px">{esc(s.get("caption"))}</div></div>' if s.get("caption") else ""
        return f'{hl}<div class="phone up" style="--d:.3s;align-self:center"><img src="file://{shot}"></div>{cap}'
    if t == "steps":
        step = min(1.2, max(0.5, (dur - 1) / max(1, len(s["steps"]))))
        rows = "".join(f'<div class="step up" style="--d:{0.4 + i * step:.2f}s"><div class="n">{i + 1}</div><div class="t">{esc(x.get("title"))}</div></div>'
                       for i, x in enumerate(s["steps"]))
        return f'{hl}<div class="card"><div class="steps">{rows}</div></div>'
    if t == "logos":
        hi = set(s.get("highlight", []))
        cells = "".join(f'<div class="gi in" style="--d:{0.3 + i * 0.12:.2f}s"><img src="{logo_uri(GAMES[g]["logo"])}" '
                        f'style="{"outline:9px solid " + YELLOW + ";outline-offset:6px" if g in hi else ""}"><div>{esc(GAMES[g]["ml"])}</div></div>'
                        for i, g in enumerate(s.get("games") or ALL_GAMES))
        return f'{hl}<div class="grid">{cells}</div>'
    if t == "text":
        return (f'<div class="h1 stroke in" style="--d:.2s">{esc(s.get("headline"))}</div>'
                + (f'<div class="h1 in" style="--d:.6s;font-size:150px">{esc(s["sub"])}</div>' if s.get("sub") else ""))
    if t == "cta":
        q = f'<div class="q in" style="--d:1.3s">{esc(s["question"])}</div>' if s.get("question") else ""
        return (f'<div class="h1 stroke in" style="--d:.15s">{esc(s.get("headline"))}</div>'
                + (f'<div class="sub up" style="--d:.45s">{esc(s["sub"])}</div>' if s.get("sub") else "")
                + f'<div class="url-big in" style="--d:.7s">{esc(CONFIG["brand"]["url"])}</div>'
                f'<div class="tag in" style="--d:1s">PLAY FREE · LINK IN BIO</div>{q}')
    raise SystemExit(f"Unknown scene type '{t}'")


def scene_html(s, gid, dur, start, total, index):
    accent = game(gid)["color"] if gid else BLUE
    bgs = [(accent, shade(accent, 1.12), "spin"), (shade(accent, 1.8), shade(accent, 1.62), "dots"),
           (YELLOW, YELLOW2, "spin"), (shade(accent, 1.8), shade(accent, 1.62), "dots")]
    if s["type"] in ("hook", "cta", "answer"):
        b1, b2, kind = accent, shade(accent, 1.12), "spin"
    else:
        b1, b2, kind = bgs[index % len(bgs)]
    color = CREAM if is_dark(b1) else INK
    title = YELLOW if luminance(b1) < 125 else CREAM
    head_label = (f'<img src="{logo_uri(game(gid)["logo"])}">{esc(game(gid)["ml"])} · {esc(game(gid)["en"])}' if gid
                  else f'{esc(CONFIG["brand"]["name_ml"])} · {esc(CONFIG["brand"]["name_en"])}')
    return (f'<!doctype html><html lang="ml"><head><meta charset="utf-8">{fonts_head()}<style>{CSS}</style></head><body>'
            f'<div class="reel" style="--b1:{b1};--b2:{b2};--title:{title};color:{color}"><div class="{kind}"></div>'
            f'<div class="progress"><i style="--total:{total:.2f}s;--start:-{start:.2f}s"></i></div>'
            f'<div class="head"><img class="badge" src="{badge_uri()}"><div class="chip">{head_label}</div></div>'
            f'<div class="stage">{scene_body(s, gid, dur)}</div>'
            f'<div class="foot">{esc(CONFIG["brand"]["url"])}</div></div></body></html>')


def resample(x, sr_from, sr_to):
    if sr_from == sr_to:
        return x
    n = int(len(x) * sr_to / sr_from)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def render(spec_path, out_dir):
    global SPEC_DIR
    SPEC_DIR = pathlib.Path(spec_path).resolve().parent
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    out = pathlib.Path(out_dir).resolve()
    frames_dir = out / ".frames"
    html_dir = out / ".html"
    for d in (out, frames_dir, html_dir):
        d.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("*.jpg"):
        old.unlink()
    gid = spec.get("game")
    voice = spec.get("voice") or voice_for_week(spec["date"])

    # 1. Voice lines and scene timings.
    lines, durs = [], []
    for s in spec["scenes"]:
        if s.get("say"):
            samples, sr = speak(s["say"], voice)
            samples = resample(samples, sr, SR)
        else:
            samples = np.zeros(0, dtype=np.float32)
        lines.append(samples)
        durs.append(max(float(s.get("min", 2.6)), len(samples) / SR + 0.75))
    total = sum(durs)
    lo, hi = CONFIG["reels"]["minSeconds"], CONFIG["reels"]["maxSeconds"]
    if not lo <= total <= hi:
        print(f"WARNING: reel is {total:.1f}s; aim for {lo}-{hi}s (shorten or lengthen the 'say' lines)")

    # 2. Audio: voice over a ducked music bed.
    seed = int(spec.get("date", "2026-01-01").replace("-", "")) % 1000
    bed = music.make(total, seed=seed) * 0.4
    mix = bed.copy()
    t0 = 0.0
    for samples, dur in zip(lines, durs):
        at = int((t0 + 0.35) * SR)
        seg = samples[: max(0, len(mix) - at)]
        mix[at:at + len(seg)] += seg * 0.95
        t0 += dur
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.95
    music.write_wav(out / ".mix.wav", mix, SR)

    # 3. Frames: each scene's CSS animations stepped frame by frame.
    k = 0
    start = 0.0
    sheet_frames = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": W, "height": H})
        for i, (s, dur) in enumerate(zip(spec["scenes"], durs)):
            path = html_dir / f"scene-{i + 1}.html"
            path.write_text(scene_html(s, gid, dur, start, total, i), encoding="utf-8")
            page.goto(f"file://{path}")
            page.evaluate("document.fonts.ready.then(() => true)")
            page.wait_for_timeout(200)
            n = int(round(dur * FPS))
            for f in range(n):
                ms = f * 1000 / FPS
                page.evaluate("(ms) => document.getAnimations().forEach(a => { a.pause(); a.currentTime = ms; })", ms)
                frame = frames_dir / f"{k:05d}.jpg"
                page.screenshot(path=str(frame), type="jpeg", quality=90)
                if f == int(n * 0.8):
                    sheet_frames.append(frame)
                k += 1
            start += dur
        browser.close()

    # 4. Encode.
    mp4 = out / "reel.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "%05d.jpg"),
                    "-i", str(out / ".mix.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", str(SR), "-shortest", "-movflags", "+faststart", str(mp4)],
                   check=True)
    cover_ms = int(min(durs[0] * 0.85, 2.4) * 1000)
    Image.open(frames_dir / f"{int(cover_ms / 1000 * FPS):05d}.jpg").save(out / "cover.jpg", quality=92)
    sheet = Image.new("RGB", (len(sheet_frames) * 270 + (len(sheet_frames) - 1) * 8, 480), "white")
    for j, fpath in enumerate(sheet_frames):
        sheet.paste(Image.open(fpath).resize((270, 480)), (j * 278, 0))
    sheet.save(out / "contact-sheet.jpg", quality=85)
    info = {"file": str(mp4), "seconds": round(total, 2), "coverMs": cover_ms, "voice": voice,
            "scenes": [round(d, 2) for d in durs], "frames": k}
    (out / "reel.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(json.dumps(info))
    return info


SPEC_DIR = pathlib.Path.cwd()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    render(sys.argv[1], sys.argv[2])
