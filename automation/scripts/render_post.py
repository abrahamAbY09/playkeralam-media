"""Render an Instagram post (1-6 slides, 1080x1350) from a JSON spec into JPEGs.

    python3 render_post.py spec.json OUT_DIR

The spec (written by the weekly run, see PLAYBOOK.md):
{
  "game": "vaakku" | null,              # null for a general Play Keralam post
  "slides": [ {"type": "hero", ...}, ..., {"type": "cta", ...} ]
}
Slide types and their fields (all text may be Malayalam, English or both; "\n" breaks a line):
  hero    kicker, title, subtitle, hook, chips[]
  screen  headline, sub, shot (PNG from shoot.py), points[] (up to 3)
  steps   headline, steps[{title, text}] (3-4)
  tiles   headline, sub, tiles[{text, color: green|yellow|grey|blank|cream|blue}], note
  cast    headline, sub, names[], hidden (count of hidden rows), note
  story   headline, sub, story, note
  pair    headline, sub, films[{title, director, cast[], date}], showDates, firstIndex
  map     headline, sub, svg (from gamedata.js), place, note
  list    headline, sub, items[]
  answer  headline, big, details[], svg (optional), tiles (optional)
  logos   headline, sub, games[] (ids; default all 11), highlight[]
  cta     headline, sub, question
Prints any layout warnings (text that had to shrink a lot, or boxes outside the frame).
"""
import json
import pathlib
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (BLUE, CONFIG, CREAM, DARK, GAMES, GREEN, INK, PINK, RED, YELLOW, YELLOW2,  # noqa: E402
                    badge_uri, esc, fonts_head, game, is_dark, logo_uri, luminance, shade)

W, H = CONFIG["posts"]["width"], CONFIG["posts"]["height"]
SPEC_DIR = pathlib.Path.cwd()
ALL_GAMES = ["vaakku", "paryayam", "thaaranira", "katha", "aadyam", "ashwamedham",
             "antakshari", "kerala-guesser", "thurupp", "cidmoosa", "sat"]

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{font-family:'Baloo Chettan 2',sans-serif;color:{INK};-webkit-font-smoothing:antialiased}}
.slide{{position:relative;width:{W}px;height:{H}px;overflow:hidden;display:flex;flex-direction:column;padding:52px 64px 44px;background:var(--b1)}}
.bg-sunburst{{background:repeating-conic-gradient(from 0deg at 50% 42%,var(--b1) 0deg 8deg,var(--b2) 8deg 16deg)}}
.bg-dots{{background-color:var(--b1);background-image:radial-gradient(var(--b2) 4px,transparent 4.6px);background-size:44px 44px}}
.bg-stripes{{background:repeating-linear-gradient(-45deg,var(--b1) 0 30px,var(--b2) 30px 60px)}}
.bg-plain{{background:var(--b1)}}
.head{{display:flex;align-items:center;gap:20px;height:100px;flex:none;position:relative;z-index:2}}
.badge{{width:100px;height:100px;border-radius:50%;border:5px solid {INK};box-shadow:6px 6px 0 {INK};background:#fff;object-fit:cover}}
.chip{{color:{INK};display:flex;align-items:center;gap:14px;background:{CREAM};border:5px solid {INK};border-radius:999px;padding:8px 30px 4px 10px;box-shadow:6px 6px 0 {INK};font-weight:800;font-size:34px;white-space:nowrap}}
.chip img{{width:58px;height:58px;border-radius:14px;margin-top:-4px}}
.main{{flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center;gap:30px;padding:26px 0 18px;position:relative;z-index:1}}
.main>*{{flex:none}}
.fit{{overflow-wrap:normal;word-break:keep-all}}
.foot{{flex:none;display:flex;justify-content:space-between;align-items:center;height:76px;font-weight:800;font-size:34px;position:relative;z-index:2}}
.foot .url{{color:{INK};background:{CREAM};border:5px solid {INK};border-radius:999px;padding:10px 26px 4px;box-shadow:6px 6px 0 {INK}}}
.foot .go{{background:{INK};color:{YELLOW};border-radius:999px;padding:12px 30px 6px;display:flex;gap:12px;align-items:center}}
.card{{color:{INK};background:{CREAM};border:7px solid {INK};border-radius:32px;box-shadow:12px 12px 0 {INK};padding:34px 42px}}
.h1{{font-weight:800;font-size:92px;line-height:1.18}}
.h2{{font-weight:800;font-size:68px;line-height:1.22}}
.sub{{font-family:'Manjari',sans-serif;font-weight:700;font-size:38px;line-height:1.35}}
.body{{font-family:'Manjari',sans-serif;font-weight:700;font-size:40px;line-height:1.4}}
.note{{align-self:flex-start;background:{INK};color:{CREAM};border-radius:20px;padding:16px 28px 10px;font-weight:800;font-size:34px;line-height:1.25;transform:rotate(-1.5deg)}}
.stroke{{-webkit-text-stroke:9px {INK};paint-order:stroke fill;text-shadow:9px 9px 0 {INK}}}
.tilt-l{{transform:rotate(-2deg)}} .tilt-r{{transform:rotate(1.5deg)}}
.chips{{display:flex;flex-wrap:wrap;gap:16px}}
.chips span{{color:{INK};background:{CREAM};border:5px solid {INK};border-radius:999px;padding:10px 26px 4px;font-weight:800;font-size:34px;box-shadow:5px 5px 0 {INK}}}
.chips span:nth-child(3n+1){{background:{YELLOW}}} .chips span:nth-child(3n+2){{background:{PINK}}}
.biglogo{{width:230px;height:230px;border-radius:52px;border:7px solid {INK};box-shadow:14px 14px 0 {INK};background:#fff;transform:rotate(-6deg)}}
.steps{{display:flex;flex-direction:column;gap:26px}}
.step{{display:flex;gap:28px;align-items:center}}
.step .n{{color:{INK};flex:none;width:104px;height:104px;border-radius:50%;border:6px solid {INK};background:{YELLOW};box-shadow:7px 7px 0 {INK};font-weight:800;font-size:60px;display:flex;align-items:center;justify-content:center;padding-top:10px}}
.step .t{{font-weight:800;font-size:46px;line-height:1.12}}
.step .x{{font-family:'Manjari',sans-serif;font-weight:700;font-size:33px;line-height:1.3;margin-top:4px}}
.tiles{{display:flex;flex-wrap:wrap;gap:20px;justify-content:center}}
.tile{{min-width:170px;height:170px;padding:22px 22px 0;border:7px solid {INK};border-radius:28px;box-shadow:9px 9px 0 {INK};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:84px;color:#fff}}
.t-green{{background:{GREEN}}} .t-yellow{{background:{YELLOW};color:{INK}}} .t-grey{{background:#9A958A}} .t-blue{{background:{BLUE}}}
.t-cream{{background:{CREAM};color:{INK}}} .t-blank{{background:{CREAM};color:{INK};border-style:dashed}}
.names{{display:flex;flex-direction:column;gap:18px}}
.name{{color:{INK};display:flex;align-items:center;gap:22px;background:{CREAM};border:6px solid {INK};border-radius:24px;box-shadow:8px 8px 0 {INK};padding:18px 28px 10px;font-weight:800;font-size:50px}}
.name .k{{flex:none;width:68px;height:68px;border-radius:50%;background:{YELLOW};border:5px solid {INK};display:flex;align-items:center;justify-content:center;font-size:38px;padding-top:6px}}
.name.hid{{background:{INK};color:{YELLOW2};letter-spacing:8px}}
.pair{{display:flex;flex-direction:column;gap:30px}}
.film{{color:{INK};position:relative;background:{CREAM};border:7px solid {INK};border-radius:30px;box-shadow:11px 11px 0 {INK};padding:30px 36px 24px 140px}}
.film .ab{{color:{INK};position:absolute;left:30px;top:50%;margin-top:-46px;width:92px;height:92px;border-radius:50%;background:{YELLOW};border:6px solid {INK};font-weight:800;font-size:52px;display:flex;align-items:center;justify-content:center;padding-top:8px}}
.film .ti{{font-weight:800;font-size:58px;line-height:1.05}}
.film .me{{font-family:'Manjari',sans-serif;font-weight:700;font-size:31px;line-height:1.35;margin-top:6px}}
.film .dt{{display:inline-block;margin-top:12px;background:{INK};color:{YELLOW};border-radius:14px;padding:8px 18px 2px;font-weight:800;font-size:34px}}
.film.win{{background:{GREEN};color:#fff}} .film.win .ab{{background:{CREAM};color:{INK}}}
.mapwrap{{display:flex;gap:30px;align-items:center;justify-content:flex-start;min-width:0}}
.mapwrap>div{{flex:none}}
.mapwrap svg{{height:760px;width:auto;border-radius:18px;filter:drop-shadow(10px 10px 0 {INK})}}
.answer .mapwrap svg{{height:600px}}
.list{{display:flex;flex-direction:column;gap:20px}}
.list div{{font-family:'Manjari',sans-serif;font-weight:700;font-size:40px;line-height:1.35;padding-left:56px;position:relative}}
.list div:before{{content:'';position:absolute;left:0;top:14px;width:30px;height:30px;border-radius:9px;background:{YELLOW};border:5px solid {INK}}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:26px 22px}}
.gi{{display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;font-weight:800;font-size:28px;line-height:1.1}}
.gi img{{width:150px;height:150px;border-radius:36px;border:6px solid {INK};box-shadow:8px 8px 0 {INK};background:#fff}}
.gi.hl img{{outline:8px solid {YELLOW};outline-offset:6px}}
.phone{{position:relative;margin:0 auto;width:430px;height:931px;border-radius:66px;border:16px solid {INK};box-shadow:16px 16px 0 {INK};overflow:hidden;background:#000;flex:none}}
.phone img{{width:100%;height:100%;object-fit:cover;object-position:top}}
.shotrow{{display:flex;gap:40px;align-items:center}}
.bubbles{{flex:1;display:flex;flex-direction:column;gap:26px}}
.bubble{{color:{INK};background:{CREAM};border:6px solid {INK};border-radius:28px;box-shadow:9px 9px 0 {INK};padding:22px 26px 14px;font-family:'Manjari',sans-serif;font-weight:700;font-size:34px;line-height:1.3}}
.bubble:nth-child(2){{background:{YELLOW}}} .bubble:nth-child(3){{background:{PINK}}}
.big{{font-weight:800;font-size:118px;line-height:1.15}}
.url-big{{color:{INK};background:{YELLOW};border:8px solid {INK};border-radius:999px;box-shadow:14px 14px 0 {INK};padding:30px 20px 18px;text-align:center;font-weight:800;font-size:76px;transform:rotate(1.5deg)}}
.tag{{align-self:center;margin-top:-30px;background:{RED};color:{CREAM};border:6px solid {INK};border-radius:16px;padding:12px 30px 6px;font-weight:800;font-size:38px;transform:rotate(-3deg)}}
"""

FIT_JS = """
(() => {
  const warns = [];
  for (const el of document.querySelectorAll('.fit')) {
    let size = parseFloat(getComputedStyle(el).fontSize), start = size;
    const maxH = parseFloat(getComputedStyle(el).maxHeight) || Infinity;
    // Malayalam glyphs reach past their line box, so compare against the box's height limit, not clientHeight.
    const over = () => el.scrollWidth > el.clientWidth + 2 || el.getBoundingClientRect().height > maxH + 2 || el.scrollHeight > maxH + 12;
    while (over() && size > 18) { size -= 2; el.style.fontSize = size + 'px'; }
    if (size < start * 0.7) warns.push('text shrank a lot (' + Math.round(start) + 'px -> ' + size + 'px): ' + el.textContent.slice(0, 50));
    if (over()) warns.push('text still overflows: ' + el.textContent.slice(0, 50));
  }
  const main = document.querySelector('.main');
  if (main && main.scrollHeight > main.clientHeight + 4) warns.push('content taller than the slide by ' + (main.scrollHeight - main.clientHeight) + 'px');
  return warns;
})()
"""


def palette(color, index):
    """Background colours for slide `index` of a post whose accent is `color`."""
    light = shade(color, 1.82)
    options = [
        (color, shade(color, 1.12), "sunburst"),
        (light, shade(color, 1.65), "dots"),
        (YELLOW, YELLOW2, "stripes"),
        (light, shade(color, 1.7), "dots"),
        (PINK, shade(PINK, 1.15), "stripes"),
    ]
    return options[index % len(options)]


def header(gid):
    if gid:
        g = game(gid)
        label = f'<img src="{logo_uri(g["logo"])}">{esc(g["ml"])} · {esc(g["en"])}'
    else:
        label = f'{esc(CONFIG["brand"]["name_ml"])} · {esc(CONFIG["brand"]["name_en"])}'
    return f'<div class="head"><img class="badge" src="{badge_uri()}"><div class="chip">{label}</div></div>'


def footer(last):
    if last:  # the big link is already on the slide
        return f'<div class="foot"><div></div><div class="go">{esc(CONFIG["brand"]["handle"])}</div></div>'
    return f'<div class="foot"><div class="url">{esc(CONFIG["brand"]["url"])}</div><div class="go">Swipe →</div></div>'


def tiles_html(tiles):
    return '<div class="tiles">' + "".join(
        f'<div class="tile t-{esc(t.get("color", "cream"))}">{esc(t.get("text", ""))}</div>' for t in tiles) + "</div>"


def text_color(bg):
    return CREAM if is_dark(bg) else INK


def slide_body(s, gid, accent):
    t = s["type"]
    hl = lambda k="headline", cls="h2": f'<div class="{cls} fit" style="max-height:330px">{esc(s.get(k))}</div>' if s.get(k) else ""  # noqa: E731
    sub = f'<div class="sub fit" style="max-height:200px">{esc(s["sub"])}</div>' if s.get("sub") else ""
    note = f'<div class="note">{esc(s["note"])}</div>' if s.get("note") else ""
    if t == "hero":
        logo = logo_uri(game(gid)["logo"]) if gid else badge_uri()
        chips = "".join(f"<span>{esc(c)}</span>" for c in s.get("chips", []))
        kicker = f'<div class="note" style="transform:rotate(-2deg)">{esc(s["kicker"])}</div>' if s.get("kicker") else ""
        return (f'<div style="display:flex;align-items:center;gap:44px"><img class="biglogo" src="{logo}">'
                f'<div style="flex:1;display:flex;flex-direction:column;gap:18px">{kicker}'
                f'<div class="h1 stroke fit" style="color:var(--title);max-height:260px">{esc(s.get("title"))}</div>'
                f'<div class="h2 fit" style="font-size:54px;max-height:140px">{esc(s.get("subtitle"))}</div></div></div>'
                f'<div class="card tilt-l"><div class="body fit" style="max-height:330px">{esc(s.get("hook"))}</div></div>'
                f'<div class="chips">{chips}</div>')
    if t == "screen":
        pts = "".join(f'<div class="bubble">{esc(p)}</div>' for p in s.get("points", [])[:3])
        shot = (SPEC_DIR / s["shot"]).resolve()
        if not shot.exists():
            raise SystemExit(f"Missing screenshot {shot}")
        return (f'{hl()}{sub}<div class="shotrow"><div class="phone"><img src="file://{shot}"></div>'
                f'<div class="bubbles">{pts}</div></div>')
    if t == "steps":
        steps = "".join(f'<div class="step"><div class="n">{i}</div><div><div class="t">{esc(x.get("title"))}</div>'
                        f'<div class="x">{esc(x.get("text"))}</div></div></div>' for i, x in enumerate(s["steps"], 1))
        return f'{hl()}<div class="card"><div class="steps">{steps}</div></div>{note}'
    if t == "tiles":
        return f'{hl()}{sub}{tiles_html(s["tiles"])}{note}'
    if t == "cast":
        rows = "".join(f'<div class="name"><div class="k">{i}</div>{esc(n)}</div>' for i, n in enumerate(s["names"], 1))
        rows += "".join(f'<div class="name hid"><div class="k" style="color:{INK};letter-spacing:0">{len(s["names"]) + j + 1}</div>? ? ? ? ?</div>'
                        for j in range(int(s.get("hidden", 0))))
        return f'{hl()}{sub}<div class="names">{rows}</div>{note}'
    if t == "story":
        return f'{hl()}{sub}<div class="card tilt-r"><div class="body fit" style="max-height:640px">{esc(s["story"])}</div></div>{note}'
    if t == "pair":
        films = []
        for i, f in enumerate(s["films"]):
            win = " win" if s.get("firstIndex") == i else ""
            date = f'<div class="dt">{esc(f.get("date"))}</div>' if s.get("showDates") and f.get("date") else ""
            meta = " · ".join(x for x in [f.get("director"), ", ".join(f.get("cast", [])[:3])] if x)
            films.append(f'<div class="film{win}"><div class="ab">{"AB"[i]}</div><div class="ti">{esc(f["title"])}</div>'
                         f'<div class="me">{esc(meta)}</div>{date}</div>')
        return f'{hl()}{sub}<div class="pair">{"".join(films)}</div>{note}'
    if t == "map":
        place = f'<div class="card tilt-l" style="padding:26px 34px"><div class="h2 fit" style="max-height:260px">{esc(s.get("place"))}</div></div>' if s.get("place") else ""
        return (f'{hl()}<div class="mapwrap"><div>{s["svg"]}</div><div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:26px">'
                f'{place}{sub}{note}</div></div>')
    if t == "list":
        items = "".join(f"<div>{esc(x)}</div>" for x in s["items"])
        return f'{hl()}{sub}<div class="card"><div class="list">{items}</div></div>{note}'
    if t == "answer":
        extra = s["svg"] if s.get("svg") else (tiles_html(s["tiles"]) if s.get("tiles") else "")
        if s.get("svg"):
            extra = f'<div class="mapwrap" style="justify-content:flex-start">{extra}</div>'
        details = "".join(f"<div>{esc(d)}</div>" for d in s.get("details", []))
        details_html = f'<div class="card"><div class="list">{details}</div></div>' if details else ""
        return (f'<div class="answer" style="display:flex;flex-direction:column;gap:26px">{hl()}<div class="big stroke fit" style="color:var(--title);max-height:300px">{esc(s.get("big"))}</div>'
                f'{extra}{details_html}</div>')
    if t == "logos":
        ids = s.get("games") or ALL_GAMES
        hi = set(s.get("highlight", []))
        cells = "".join(f'<div class="gi{" hl" if i in hi else ""}"><img src="{logo_uri(GAMES[i]["logo"])}">'
                        f'<div>{esc(GAMES[i]["ml"])}</div></div>' for i in ids)
        return f'{hl()}{sub}<div class="grid">{cells}</div>'
    if t == "cta":
        q = f'<div class="note" style="background:{PINK};color:{INK};border:6px solid {INK}">{esc(s["question"])}</div>' if s.get("question") else ""
        return (f'<div class="h1 stroke fit" style="color:var(--title);max-height:340px">{esc(s.get("headline"))}</div>'
                f'{sub}<div class="url-big">{esc(CONFIG["brand"]["url"])}</div>'
                f'<div class="tag">PLAY FREE · LINK IN BIO</div>{q}')
    raise SystemExit(f"Unknown slide type '{t}'")


def build_html(spec, i, total):
    s = spec["slides"][i]
    gid = spec.get("game")
    accent = spec.get("accent") or (game(gid)["color"] if gid else BLUE)
    if s["type"] in ("hero", "cta"):
        b1, b2, pattern = accent, shade(accent, 1.12), "sunburst"
    else:
        b1, b2, pattern = palette(accent, i)
    color = text_color(b1)
    title = YELLOW if luminance(b1) < 125 else CREAM
    style = f"--b1:{b1};--b2:{b2};--title:{title};color:{color}"
    return (f'<!doctype html><html lang="ml"><head><meta charset="utf-8">{fonts_head()}<style>{CSS}</style></head>'
            f'<body><div class="slide bg-{pattern}" style="{style}">{header(gid)}'
            f'<div class="main">{slide_body(s, gid, accent)}</div>{footer(i == total - 1)}</div></body></html>')


def render(spec_path, out_dir):
    global SPEC_DIR
    SPEC_DIR = pathlib.Path(spec_path).resolve().parent
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    out = pathlib.Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = out / ".html"
    work.mkdir(exist_ok=True)
    total = len(spec["slides"])
    lo, hi = CONFIG["posts"]["minSlides"], CONFIG["posts"]["maxSlides"]
    if not lo <= total <= hi:
        print(f"WARNING: {total} slides; aim for {lo}-{hi}")
    files, warnings = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": W, "height": H})
        for i in range(total):
            html_path = work / f"slide-{i + 1}.html"
            html_path.write_text(build_html(spec, i, total), encoding="utf-8")
            page.goto(f"file://{html_path}")
            page.evaluate("document.fonts.ready.then(() => true)")
            page.wait_for_timeout(250)
            warnings += [f"slide {i + 1}: {w}" for w in page.evaluate(FIT_JS)]
            png = work / f"slide-{i + 1}.png"
            page.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": W, "height": H})
            jpg = out / f"slide-{i + 1}.jpg"
            Image.open(png).convert("RGB").save(jpg, "JPEG", quality=CONFIG["posts"]["jpegQuality"], subsampling=0, optimize=True)
            files.append(jpg)
        browser.close()
    sheet = Image.new("RGB", (len(files) * 540 + (len(files) - 1) * 12, 675), "white")
    for k, f in enumerate(files):
        sheet.paste(Image.open(f).resize((540, 675)), (k * 552, 0))
    sheet.save(out / "contact-sheet.jpg", quality=85)
    for f in files:
        print("wrote", f)
    for w in warnings:
        print("WARNING:", w)
    return files, warnings


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    render(sys.argv[1], sys.argv[2])
