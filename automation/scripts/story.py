"""The "story" reel look (25 Nov 2026, Abr: reels are now 30-45 s and tell a little story instead of explaining
features). A flat, warm illustration style: a recurring cast of four Kerala characters acting out a short plot in a
real-looking place (a family living room, a tea shop, a bus stop, a night terrace), with speech bubbles in English
for their Malayalam lines, camera moves, reaction effects, and the game's REAL screen held up large on a phone.

Use it with "theme": "story" in a reel spec. render_reel.py calls scene_html() below for every scene and passes
each beat's voice length in s["_lens"] so mouths move only while a character speaks.

THE CAST (ids; "speaker" in a beat picks who talks and which voice is used)
  ammachi  grandmother: white hair bun, glasses, kasavu set-mundu. Sharp, calm, quietly wins.
  uncle    Kuttan uncle: moustache, balding, shirt and mundu, a belly. Over-confident know-it-all.
  appu     Appu, about 20: curly hair, mustard hoodie, jeans, always on his phone. Brings in the game.
  meenu    Meenu, about 20: long braid with jasmine, pink churidar. Competitive, sarcastic.
  narrator no body; a yellow caption box instead of a bubble.

SCENE TYPES (scene fields; per-beat fields in [ ])
  hook / shot  setting, tint?, cast[{id, x?, pose?, mood?, prop?, flip?, scale?}]
               [say, speaker, text, style: bubble|caption|big|tag, mood{id: mood}, pose{id: pose}, cam, fx, on,
                answer{kicker, title, sub}, dur, gap, sfx]
               The first scene of a reel must be "hook": its first beat's text is on screen at frame 0.
  phone        setting (blurred behind), shot (file in the spec folder), crop [x, y, w, h] in screenshot px,
               hand: left|right [say, speaker, text, style, chip (a line added on the screen, e.g. a clue),
               timer (seconds: a ring that drains; add silent "dur" beats with "sfx": "tick"), answer{...}]
  loop         setting, tint?, cast[...] [say, speaker, text, style, url (true: the text is the URL sign),
               echo (text: clears the stage and brings the hook line back so a replay flows on)]

  moods  normal, happy, smug, shock, sad, angry, think, laugh, proud
  poses  down, point, shrug, head (hands on head), phone, chin, wave, fist, cross, paper, tea, cards
  cam    wide (default), <cast id> (close-up), two:<id>,<id>; a beat's cam holds until another beat changes it
  fx     shake (the whole frame), sweat, qmarks, bulb, spark, steam, hearts, lines; "on" names the character
         (default: the speaker)
  settings  living-room, tea-shop, bus-stop, night-terrace;  tint  morning | evening | night (optional)

All text sits inside Meta's Reels safe zone (y 270-1250, x 65-960); faces are placed inside it too. Backgrounds and
bodies bleed to the full frame. No sunburst, dots, cream cards, badge pill, bottom CTA pill or floating phone.
"""
import math
import pathlib

from common import esc as _esc

SAFE = dict(top=270, bottom=1250, left=65, right=960)
PAD = 10
STAGE_W = SAFE["right"] - SAFE["left"] - 2 * PAD
INK = "#1E140E"
CREAM = "#FFF4DC"
SUN = "#FFD23F"
MOUTH = "#5B1A16"

HEAD_Y = 790        # scene y of a head centre in a wide shot
CLOSE = (540, 905)  # where a close-up puts the speaker's head
LOCAL_HEAD = (200, 205)


def d(t):
    return f"animation-delay:{t:.3f}s"


def esc(t):
    return _esc(t)


def win(a, b=None):
    """Inline style that shows an element only from scene time a to b."""
    if a <= 0.001:
        return f"animation:off .01s linear {b:.3f}s forwards" if b is not None else ""
    off = f",off .01s linear {b:.3f}s forwards" if b is not None else ""
    return f"opacity:0;animation:on .01s linear {a:.3f}s forwards{off}"


# ----------------------------------------------------------------------------------------------------- the cast
CAST = {
    "ammachi": dict(skin="#B47450", shade="#9A5E3E", hair="#E4DED3", top="#F6F0E2", sleeve="#F6F0E2",
                    forearm="skin", lower="mundu", lowc="#F6F0E2", trim="#D4A033", scale=0.93, voice="female_old"),
    "uncle": dict(skin="#93573A", shade="#7A4630", hair="#2A2320", top="#7DB2D8", sleeve="#7DB2D8",
                  forearm="skin", lower="mundu", lowc="#F3F0E8", trim="#C9A227", scale=1.0, voice="male_mid", belly=True),
    "appu": dict(skin="#A4643F", shade="#8A5234", hair="#18120F", top="#E8A33A", sleeve="#E8A33A",
                 forearm="sleeve", lower="jeans", lowc="#2F4A6D", trim="#F3F3F3", scale=0.97, voice="male_young"),
    "meenu": dict(skin="#B27650", shade="#985F40", hair="#16110E", top="#C2185B", sleeve="#C2185B",
                  forearm="sleeve", lower="churidar", lowc="#F6E7C8", trim="#F2B705", scale=0.95, voice="female_young"),
}
VOICE_OF = {k: v["voice"] for k, v in CAST.items()}
VOICE_OF["narrator"] = "narrator"

SHOULDER_L, SHOULDER_R = (84, 372), (316, 372)
POSES = {  # (elbow, hand) for the left arm, then the right arm, in local px
    "down": (((66, 545), (78, 700)), ((334, 545), (322, 700))),
    "point": (((66, 545), (78, 700)), ((420, 330), (520, 250))),
    "shrug": (((14, 500), (-10, 380)), ((386, 500), (410, 380))),
    "head": (((6, 300), (104, 168)), ((394, 300), (296, 168))),
    "phone": (((84, 585), (168, 505)), ((316, 585), (232, 505))),
    "chin": (((66, 545), (78, 700)), ((330, 560), (236, 300))),
    "wave": (((66, 545), (78, 700)), ((430, 300), (440, 150))),
    "fist": (((66, 545), (78, 700)), ((400, 250), (360, 110))),
    "cross": (((70, 540), (262, 520)), ((330, 540), (138, 500))),
    "paper": (((70, 560), (112, 520)), ((330, 560), (288, 520))),
    "tea": (((66, 545), (78, 700)), ((334, 590), (250, 470))),
    "cards": (((84, 585), (168, 505)), ((316, 585), (232, 505))),
}
POSE_PROP = {"phone": "phone", "paper": "paper", "tea": "tea", "cards": "cards"}


def _arm(sh, el, ha, c, wave=False):
    sleeve = c["sleeve"]
    fore = c["skin"] if c["forearm"] == "skin" else sleeve
    cls = ' class="wave"' if wave else ""
    tf = f' style="transform-origin:{el[0]}px {el[1]}px"' if wave else ""
    return (f'<path d="M{sh[0]} {sh[1]} L{el[0]} {el[1]}" stroke="{sleeve}" stroke-width="56" stroke-linecap="round" fill="none"/>'
            f'<g{cls}{tf}><path d="M{el[0]} {el[1]} L{ha[0]} {ha[1]}" stroke="{fore}" stroke-width="48" stroke-linecap="round" fill="none"/>'
            f'<circle cx="{ha[0]}" cy="{ha[1]}" r="29" fill="{c["skin"]}"/></g>')


def _prop(kind):
    if kind == "phone":
        return ('<rect x="146" y="380" width="108" height="190" rx="18" fill="#15171C"/>'
                '<rect x="154" y="392" width="92" height="160" rx="10" fill="#6FD3FF" class="glow"/>')
    if kind == "paper":
        return ('<g transform="rotate(-4 200 520)"><rect x="70" y="420" width="260" height="230" fill="#F2EEE3" stroke="#B9B2A3" stroke-width="4"/>'
                '<rect x="88" y="440" width="224" height="26" fill="#3A3A3A"/>'
                + "".join(f'<rect x="88" y="{480 + 18 * k}" width="{104 if k % 3 else 224}" height="8" fill="#9C968A"/>' for k in range(9))
                + "".join(f'<rect x="208" y="{480 + 18 * k}" width="104" height="8" fill="#9C968A"/>' for k in range(9) if k % 3)
                + '</g>')
    if kind == "tea":
        return ('<path d="M226 418 L274 418 L268 488 L232 488 Z" fill="#E9D7B0" opacity=".9" stroke="#fff" stroke-width="3"/>'
                '<path d="M229 432 L271 432 L268 486 L232 486 Z" fill="#B06A2E"/>'
                '<path class="steam" d="M240 404 q-12 -24 0 -46 q12 -22 0 -44" stroke="#fff" stroke-width="6" fill="none" opacity=".7"/>')
    if kind == "cards":
        return "".join(f'<g transform="rotate({a} 200 560)"><rect x="168" y="430" width="64" height="96" rx="8" fill="#FBFBF7" stroke="#2A2A2A" stroke-width="3"/>'
                       f'<text x="200" y="490" font-size="40" text-anchor="middle" fill="{col}" font-weight="800">{s}</text></g>'
                       for a, col, s in ((-24, "#C62828", "♥"), (-8, "#1E1E1E", "♠"), (8, "#C62828", "♦"), (24, "#1E1E1E", "♣")))
    return ""


def _face(mood):
    ink = INK
    eye = lambda x, y, rx=11, ry=14: f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{ink}"/><circle cx="{x + 4}" cy="{y - 5}" r="4" fill="#fff"/>'
    brow = lambda x1, y1, x2, y2: f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{ink}" stroke-width="9" stroke-linecap="round"/>'
    arc = lambda p: f'<path d="{p}" stroke="{ink}" stroke-width="8" stroke-linecap="round" fill="none"/>'
    nose = arc("M194 226 Q200 240 208 230")
    eyes_n = f'<g class="blink">{eye(162, 205)}{eye(238, 205)}</g>'
    if mood == "happy":
        return (eyes_n + brow(144, 166, 180, 160) + brow(220, 160, 256, 166) + nose +
                f'<path d="M168 250 Q200 300 232 250 Z" fill="{MOUTH}"/><path d="M174 252 L226 252 L222 262 L178 262 Z" fill="#fff"/>')
    if mood == "smug":
        return (f'<ellipse cx="162" cy="207" rx="12" ry="6" fill="{ink}"/><ellipse cx="238" cy="207" rx="12" ry="6" fill="{ink}"/>'
                + brow(144, 172, 180, 172) + brow(220, 158, 256, 168) + nose + arc("M180 262 Q206 272 228 250"))
    if mood == "shock":
        return ('<circle cx="162" cy="204" r="20" fill="#fff"/><circle cx="238" cy="204" r="20" fill="#fff"/>'
                f'<g class="blink"><circle cx="162" cy="206" r="9" fill="{ink}"/><circle cx="238" cy="206" r="9" fill="{ink}"/></g>'
                + brow(142, 160, 180, 150) + brow(220, 150, 258, 160) + nose + f'<ellipse cx="200" cy="266" rx="17" ry="24" fill="{MOUTH}"/>')
    if mood == "sad":
        return (eyes_n + brow(146, 172, 180, 160) + brow(220, 160, 254, 172) + nose + arc("M180 272 Q200 256 220 272"))
    if mood == "angry":
        return (eyes_n + brow(144, 160, 182, 176) + brow(218, 176, 256, 160) + nose + arc("M180 270 Q200 262 220 270"))
    if mood == "think":
        return (f'<g class="blink">{eye(168, 199)}{eye(244, 199)}</g>' + brow(144, 172, 180, 170) + brow(220, 158, 256, 164)
                + nose + arc("M186 266 L216 260"))
    if mood == "laugh":
        return (arc("M148 210 Q162 192 176 210") + arc("M224 210 Q238 192 252 210") + brow(144, 164, 180, 158)
                + brow(220, 158, 256, 164) + nose + f'<path d="M166 248 Q200 312 234 248 Z" fill="{MOUTH}"/>'
                '<path d="M172 250 L228 250 L224 262 L176 262 Z" fill="#fff"/>')
    if mood == "proud":
        return (arc("M148 204 Q162 214 176 204") + arc("M224 204 Q238 214 252 204") + brow(144, 170, 180, 166)
                + brow(220, 166, 256, 170) + nose + arc("M176 256 Q200 280 224 256"))
    return eyes_n + brow(146, 170, 180, 166) + brow(220, 166, 254, 170) + nose + arc("M178 258 Q200 276 222 258")


def _hair_back(cid, c):
    if cid == "ammachi":
        return f'<circle cx="200" cy="92" r="44" fill="{c["hair"]}"/><circle cx="200" cy="92" r="44" fill="none" stroke="#C9C2B5" stroke-width="5"/>'
    if cid == "meenu":
        braid = "".join(f'<ellipse cx="{300 + 6 * k}" cy="{330 + 58 * k}" rx="30" ry="36" fill="{c["hair"]}"/>' for k in range(6))
        jas = "".join(f'<circle cx="{282 + 8 * k}" cy="{300 + 30 * k}" r="9" fill="#fff"/>' for k in range(5))
        return (f'<path d="M98 230 Q86 70 200 70 Q314 70 302 230 L300 330 L100 330 Z" fill="{c["hair"]}"/>{braid}{jas}')
    return ""


def _hair_front(cid, c):
    h = c["hair"]
    if cid == "ammachi":
        return (f'<path d="M106 206 Q104 98 200 96 Q296 98 294 206 Q282 140 200 130 Q118 140 106 206 Z" fill="{h}"/>'
                '<path d="M200 98 L200 132" stroke="#C9C2B5" stroke-width="4"/>'
                '<g fill="none" stroke="#6A4A2A" stroke-width="6"><circle cx="162" cy="206" r="28"/><circle cx="238" cy="206" r="28"/>'
                '<path d="M190 204 Q200 196 210 204"/></g>'
                '<circle cx="110" cy="244" r="9" fill="#E0B13A"/><circle cx="290" cy="244" r="9" fill="#E0B13A"/>')
    if cid == "uncle":
        return (f'<ellipse cx="112" cy="196" rx="24" ry="52" fill="{h}"/><ellipse cx="288" cy="196" rx="24" ry="52" fill="{h}"/>'
                '<ellipse cx="176" cy="128" rx="34" ry="16" fill="#fff" opacity=".22"/>'
                f'<path d="M156 246 Q178 232 200 242 Q222 232 244 246 Q236 266 200 256 Q164 266 156 246 Z" fill="{h}"/>')
    if cid == "appu":
        curls = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{h}"/>' for x, y, r in (
            (112, 170, 30), (128, 128, 34), (160, 100, 36), (200, 92, 38), (240, 100, 36), (272, 128, 34), (288, 170, 30),
            (150, 140, 30), (200, 128, 30), (250, 140, 30)))
        return curls + f'<path d="M160 296 Q200 318 240 296" stroke="{c["shade"]}" stroke-width="6" fill="none" opacity=".5"/>'
    if cid == "meenu":
        return (f'<path d="M104 214 Q100 90 200 88 Q300 90 296 214 Q270 136 206 128 L200 140 L194 128 Q130 136 104 214 Z" fill="{h}"/>'
                '<circle cx="200" cy="166" r="7" fill="#D3202A"/>'
                '<circle cx="110" cy="246" r="10" fill="#F2B705"/><circle cx="290" cy="246" r="10" fill="#F2B705"/>')
    return ""


def _body(cid, c):
    skin, top, low = c["skin"], c["top"], c["lowc"]
    out = []
    if c["lower"] == "mundu":
        out.append(f'<path d="M92 690 L308 690 L332 1104 L68 1104 Z" fill="{low}"/>'
                   f'<path d="M80 1050 L320 1050 L326 1078 L74 1078 Z" fill="{c["trim"]}"/>'
                   f'<path d="M210 700 L222 1100" stroke="#D9D3C4" stroke-width="5"/>')
        out.append(f'<ellipse cx="150" cy="1112" rx="46" ry="14" fill="#5A3A26"/><ellipse cx="250" cy="1112" rx="46" ry="14" fill="#5A3A26"/>')
    elif c["lower"] == "jeans":
        out.append(f'<path d="M108 690 L198 690 L194 1096 L122 1096 Z" fill="{low}"/><path d="M202 690 L292 690 L278 1096 L206 1096 Z" fill="{low}"/>'
                   '<ellipse cx="158" cy="1106" rx="52" ry="20" fill="#F3F3F3"/><ellipse cx="242" cy="1106" rx="52" ry="20" fill="#F3F3F3"/>')
    else:  # churidar: kurta to the knee, leggings
        out.append(f'<path d="M134 900 L190 900 L184 1096 L142 1096 Z" fill="{low}"/><path d="M210 900 L266 900 L258 1096 L216 1096 Z" fill="{low}"/>'
                   f'<path d="M96 680 L304 680 L346 960 L54 960 Z" fill="{top}"/>'
                   f'<path d="M60 930 L340 930 L346 960 L54 960 Z" fill="{c["trim"]}"/>'
                   '<ellipse cx="162" cy="1104" rx="40" ry="13" fill="#7A3B2A"/><ellipse cx="238" cy="1104" rx="40" ry="13" fill="#7A3B2A"/>')
    if c.get("belly"):
        torso = "M118 336 Q200 318 282 336 L338 368 Q392 560 312 712 L88 712 Q8 560 62 368 Z"
    else:
        torso = "M120 336 Q200 320 280 336 L330 366 Q348 520 304 706 L96 706 Q52 520 70 366 Z"
    out.append(f'<rect x="172" y="282" width="56" height="70" fill="{c["shade"]}"/>')
    out.append(f'<path d="{torso}" fill="{top}"/>')
    if cid == "uncle":
        out.append('<path d="M172 338 L200 392 L228 338" fill="#5E95BE"/><rect x="232" y="430" width="52" height="56" rx="6" fill="none" stroke="#5E95BE" stroke-width="5"/>'
                   '<rect x="246" y="414" width="8" height="40" fill="#1E3B8A"/>'
                   + "".join(f'<circle cx="200" cy="{420 + 70 * k}" r="7" fill="#F4F4F4"/>' for k in range(4)))
    elif cid == "appu":
        out.append('<path d="M140 336 Q200 410 260 336" fill="none" stroke="#C98A26" stroke-width="10"/>'
                   '<rect x="140" y="560" width="120" height="70" rx="20" fill="#D69130"/>'
                   '<path d="M182 360 L176 470 M218 360 L224 470" stroke="#F6F1E6" stroke-width="6"/>')
    elif cid == "ammachi":
        out.append(f'<path d="M110 340 L300 690 L250 706 L80 400 Z" fill="#FBF6EA"/>'
                   f'<path d="M110 340 L300 690" stroke="{c["trim"]}" stroke-width="14"/>'
                   f'<path d="M150 336 Q200 360 250 336" stroke="{c["trim"]}" stroke-width="8" fill="none"/>')
    elif cid == "meenu":
        out.append(f'<path d="M80 372 Q200 470 320 372 L330 410 Q200 520 70 410 Z" fill="#F2B705" opacity=".95"/>'
                   '<path d="M168 338 Q200 372 232 338" stroke="#8E1042" stroke-width="7" fill="none"/>')
    return "".join(out)


def character(cid, segments, talks, blink_delay):
    """One cast member as SVG (local 400 x 1150, head centre at 200,205). segments: [(a, b, mood, pose)];
    talks: [(a, b)] windows when this character speaks (the mouth flaps)."""
    c = CAST[cid]
    parts = [_hair_back(cid, c), _body(cid, c)]
    parts.append(f'<ellipse cx="110" cy="216" rx="17" ry="25" fill="{c["skin"]}"/><ellipse cx="290" cy="216" rx="17" ry="25" fill="{c["skin"]}"/>'
                 f'<ellipse cx="200" cy="205" rx="92" ry="104" fill="{c["skin"]}"/>'
                 f'<ellipse cx="160" cy="246" rx="18" ry="10" fill="#E07A5F" opacity=".25"/><ellipse cx="240" cy="246" rx="18" ry="10" fill="#E07A5F" opacity=".25"/>')
    for a, b, mood, pose in segments:
        parts.append(f'<g style="{win(a, b)}">{_face(mood)}</g>'.replace('class="blink"', f'class="blink" style="{d(blink_delay)}"'))
    for a, b in talks:
        parts.append(f'<g style="{win(a, b)}"><ellipse cx="200" cy="266" rx="36" ry="26" fill="{c["skin"]}"/>'
                     f'<ellipse class="flap" cx="200" cy="264" rx="19" ry="15" fill="{MOUTH}"/></g>')
    parts.append(_hair_front(cid, c))
    for a, b, mood, pose in segments:
        (el_l, ha_l), (el_r, ha_r) = POSES.get(pose, POSES["down"])
        arms = _arm(SHOULDER_L, el_l, ha_l, c) + _arm(SHOULDER_R, el_r, ha_r, c, wave=(pose == "wave"))
        parts.append(f'<g style="{win(a, b)}">{_prop(POSE_PROP.get(pose, ""))}{arms}</g>')
    return "".join(parts)


# --------------------------------------------------------------------------------------------------- settings
def _palm(x, y, s=1.0, col="#2F7D32", trunk="#7A5230", cls="sway"):
    fronds = "".join(f'<path d="M0 0 Q{60 * k} {-70 + 20 * abs(k)} {130 * k} {10 + 30 * abs(k)} Q{60 * k} {-30 + 20 * abs(k)} 0 0 Z" fill="{col}"/>'
                     for k in (-1.2, -0.7, -0.25, 0.25, 0.7, 1.2))
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M0 0 Q30 300 -10 700" stroke="{trunk}" stroke-width="34" fill="none"/>'
            f'<g class="{cls}" style="transform-origin:0 0">{fronds}<circle cx="0" cy="8" r="16" fill="#6B4A1E"/></g></g>')


def setting_svg(name):
    if name == "tea-shop":
        jars = "".join(f'<g transform="translate({110 + 104 * k} 452)"><rect x="0" y="0" width="80" height="104" rx="16" fill="#DDF3F2" opacity=".55" stroke="#fff" stroke-width="4"/>'
                       f'<rect x="8" y="44" width="64" height="54" rx="10" fill="{col}"/><rect x="10" y="-14" width="60" height="18" rx="5" fill="#C0392B"/></g>'
                       for k, col in enumerate(("#F39C12", "#E74C3C", "#F1C40F", "#8E44AD", "#27AE60")))
        bananas = "".join(f'<path d="M{-40 + 16 * k} {40 + 22 * (k % 3)} q30 70 80 76" stroke="#F4C430" stroke-width="22" stroke-linecap="round" fill="none"/>'
                          for k in range(6))
        return ('<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3AA29C"/><stop offset="1" stop-color="#1F6D69"/></linearGradient></defs>'
                '<rect width="1080" height="1920" fill="url(#bg)"/>'
                + "".join(f'<rect x="{40 + 140 * k}" y="0" width="56" height="1500" fill="#fff" opacity=".035"/>' for k in range(8))
                + '<rect x="96" y="300" width="470" height="120" rx="10" fill="#F6E7B6" stroke="#5B3A1E" stroke-width="10"/>'
                '<text x="331" y="384" font-family="Anton,Baloo Chettan 2" font-size="72" text-anchor="middle" fill="#B3261E">TEA · SNACKS</text>'
                '<rect x="80" y="556" width="560" height="22" fill="#6E4524"/>' + jars +
                '<g transform="translate(690 470)"><rect width="190" height="104" rx="18" fill="#7B4A26"/><circle cx="56" cy="54" r="34" fill="#3A2614"/>'
                '<circle cx="56" cy="54" r="22" fill="#5C3D22"/><rect x="108" y="26" width="64" height="16" rx="6" fill="#E6C79A"/>'
                '<rect x="108" y="56" width="64" height="10" rx="4" fill="#E6C79A"/></g>'
                '<g class="swing" style="transform-origin:880px 250px"><path d="M880 250 L880 330" stroke="#5B3A1E" stroke-width="10"/>'
                f'<g transform="translate(880 330)">{bananas}</g></g>'
                '<g transform="translate(860 860)"><path d="M0 0 L160 0 L140 380 L20 380 Z" fill="#B9A27A"/><rect x="-14" y="-30" width="188" height="40" rx="12" fill="#8C7350"/>'
                '<path class="steam" d="M60 -40 q-14 -30 0 -60 q14 -30 0 -60" stroke="#fff" stroke-width="10" fill="none" opacity=".6"/>'
                '<path class="steam s2" d="M100 -40 q-14 -30 0 -60 q14 -30 0 -60" stroke="#fff" stroke-width="10" fill="none" opacity=".5"/></g>'
                '<rect x="40" y="1360" width="1000" height="34" rx="8" fill="#6E4524"/><rect x="80" y="1394" width="26" height="150" fill="#5A381C"/>'
                '<rect x="974" y="1394" width="26" height="150" fill="#5A381C"/>'
                '<rect x="0" y="1540" width="1080" height="380" fill="#8E8B84"/><rect x="0" y="1540" width="1080" height="14" fill="#6F6C66"/>')
    if name == "bus-stop":
        return ('<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6EC1EC"/><stop offset=".62" stop-color="#FFE2A0"/></linearGradient>'
                '<radialGradient id="sun"><stop offset="0" stop-color="#FFF6C8"/><stop offset="1" stop-color="#FFF6C8" stop-opacity="0"/></radialGradient></defs>'
                '<rect width="1080" height="1920" fill="url(#bg)"/><circle cx="860" cy="430" r="200" fill="url(#sun)"/><circle cx="860" cy="430" r="78" fill="#FFF1B0"/>'
                '<path d="M0 980 Q200 860 420 950 Q640 840 860 930 Q980 880 1080 920 L1080 1300 L0 1300 Z" fill="#5DA35A"/>'
                '<path d="M0 1080 Q260 980 520 1060 Q800 990 1080 1050 L1080 1300 L0 1300 Z" fill="#3E8A47"/>'
                + _palm(980, 640, 0.9) + _palm(120, 700, 0.75, "#2E6F30") +
                '<g class="bus"><g transform="translate(1100 1010)"><rect width="760" height="330" rx="40" fill="#C8302A"/>'
                '<rect y="220" width="760" height="40" fill="#F2B705"/>'
                + "".join(f'<rect x="{40 + 120 * k}" y="40" width="96" height="120" rx="12" fill="#BFE6F5"/><circle cx="{88 + 120 * k}" cy="120" r="26" fill="#2B2B2B" opacity=".55"/>' for k in range(6))
                + '<circle cx="150" cy="330" r="52" fill="#222"/><circle cx="610" cy="330" r="52" fill="#222"/><circle cx="150" cy="330" r="20" fill="#888"/><circle cx="610" cy="330" r="20" fill="#888"/></g></g>'
                '<rect x="40" y="790" width="700" height="46" rx="10" fill="#2E5E8C"/><rect x="70" y="836" width="24" height="700" fill="#3B3B3B"/><rect x="690" y="836" width="24" height="700" fill="#3B3B3B"/>'
                '<rect x="0" y="1500" width="1080" height="420" fill="#5A5E62"/><rect x="0" y="1500" width="1080" height="20" fill="#C9C9C1"/>'
                '<g class="road">' + "".join(f'<rect x="{-200 + 260 * k}" y="1720" width="150" height="18" fill="#F4F4EE"/>' for k in range(8)) + '</g>')
    if name == "night-terrace":
        stars = "".join(f'<circle class="tw" style="{d((k * 0.37) % 2)}" cx="{(k * 197) % 1060 + 10}" cy="{(k * 131) % 760 + 40}" r="{2 + k % 3}" fill="#FFF7D6"/>'
                        for k in range(26))
        bulbs = "".join(f'<circle class="bulb" style="{d((k * 0.23) % 1.4)}" cx="{20 + 70 * k}" cy="{560 + int(80 * ((k - 7.5) / 7.5) ** 2 * -1 + 80)}" r="14" fill="#FFD36B"/>'
                        for k in range(16))
        return ('<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0E1A3A"/><stop offset="1" stop-color="#3B2A6B"/></linearGradient></defs>'
                f'<rect width="1080" height="1920" fill="url(#bg)"/>{stars}'
                '<circle cx="830" cy="380" r="70" fill="#FFF3C4"/><circle cx="860" cy="360" r="66" fill="#16224A"/>'
                + _palm(120, 820, 0.95, "#0C1530", "#0C1530") + _palm(1010, 780, 0.8, "#0C1530", "#0C1530") +
                '<path d="M0 560 Q540 720 1080 560" stroke="#2A2A2A" stroke-width="4" fill="none"/>' + bulbs +
                '<rect x="0" y="1320" width="1080" height="240" fill="#6C6A8E"/><rect x="0" y="1320" width="1080" height="26" fill="#8C8AAE"/>'
                '<rect x="0" y="1560" width="1080" height="360" fill="#3E3B5C"/>')
    # living-room (default)
    bars = "".join(f'<rect x="{640 + 44 * k}" y="372" width="12" height="520" fill="#4A2A12"/>' for k in range(7))
    return ('<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F2C47A"/><stop offset="1" stop-color="#DC9A50"/></linearGradient>'
            '<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8FD4F2"/><stop offset="1" stop-color="#FFE9B8"/></linearGradient>'
            '<linearGradient id="fl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#B2452F"/><stop offset="1" stop-color="#7E2A1C"/></linearGradient></defs>'
            '<rect width="1080" height="1920" fill="url(#bg)"/>'
            '<rect x="600" y="330" width="380" height="600" fill="#5A3418"/><rect x="630" y="360" width="320" height="540" fill="url(#sky)"/>'
            '<path d="M630 820 Q760 760 950 800 L950 900 L630 900 Z" fill="#5DA35A"/>'
            + _palm(820, 560, 0.55) + bars +
            '<rect x="600" y="618" width="380" height="16" fill="#5A3418"/>'
            '<g transform="translate(140 430)"><rect width="200" height="240" fill="#6B3E1E"/><rect x="16" y="16" width="168" height="208" fill="#E9D6B0"/>'
            '<circle cx="100" cy="96" r="40" fill="#9C7A55"/><path d="M40 224 Q100 140 160 224 Z" fill="#9C7A55"/>'
            '<path d="M20 4 Q100 -40 180 4" stroke="#E86E2E" stroke-width="10" fill="none"/></g>'
            '<g transform="translate(440 420)"><circle r="62" fill="#F8F1E0" stroke="#6B3E1E" stroke-width="10"/>'
            '<rect class="hand" x="-4" y="-46" width="8" height="48" fill="#222" style="transform-origin:0 0"/><rect x="-5" y="-30" width="10" height="32" fill="#222" transform="rotate(70)"/></g>'
            '<g transform="translate(540 0)"><rect x="-6" y="0" width="12" height="120" fill="#3A3A3A"/><circle cy="126" r="26" fill="#3A3A3A"/>'
            '<ellipse class="fan" cx="0" cy="130" rx="230" ry="12" fill="#4A4A4A" opacity=".7"/>'
            '<ellipse class="fan f2" cx="0" cy="130" rx="230" ry="12" fill="#4A4A4A" opacity=".7"/></g>'
            '<rect x="0" y="1180" width="1080" height="400" fill="#C9813F"/><rect x="0" y="1180" width="1080" height="14" fill="#8F5426"/>'
            '<g transform="translate(70 1300)"><rect width="940" height="40" rx="10" fill="#6B3A1A"/>'
            + "".join(f'<rect x="{30 + 110 * k}" y="-150" width="40" height="150" rx="6" fill="#7E4722"/>' for k in range(9))
            + '<rect y="-170" width="940" height="28" rx="10" fill="#6B3A1A"/></g>'
            '<g transform="translate(980 1280)"><rect x="-8" y="0" width="16" height="250" fill="#C9962E"/><ellipse cy="250" rx="50" ry="14" fill="#B8862A"/>'
            '<ellipse cy="0" rx="46" ry="12" fill="#D8A83A"/><path class="flame" d="M0 -10 Q16 -40 0 -74 Q-16 -40 0 -10 Z" fill="#FFB52E"/></g>'
            '<rect x="0" y="1560" width="1080" height="360" fill="url(#fl)"/><rect x="0" y="1600" width="1080" height="60" fill="#fff" opacity=".08"/>')


TINTS = {"morning": "linear-gradient(180deg,rgba(255,236,190,.20),rgba(255,236,190,0) 60%)",
         "evening": "linear-gradient(180deg,rgba(255,120,60,.22),rgba(120,40,90,.18))",
         "night": "linear-gradient(180deg,rgba(10,20,60,.45),rgba(20,10,50,.35))"}

# ------------------------------------------------------------------------------------------------------- CSS
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden;background:#000}
body{font-family:'Baloo Chettan 2',sans-serif;color:#1E140E;-webkit-font-smoothing:antialiased}
.reel{position:relative;width:1080px;height:1920px;overflow:hidden}
.drift{position:absolute;inset:0;transform-origin:50% 45%;animation:drift var(--dur) linear both}
@keyframes drift{from{transform:scale(1)}to{transform:scale(1.045)}}
.shk{position:absolute;inset:0}
.cam{position:absolute;left:0;top:0;width:1080px;height:1920px;transform-origin:0 0}
.bgsvg{position:absolute;inset:0;width:1080px;height:1920px}
.tint{position:absolute;inset:0;pointer-events:none}
.char{position:absolute;overflow:visible}
.idle{animation:idle 1.7s ease-in-out infinite alternate}
@keyframes idle{from{transform:translateY(0)}to{transform:translateY(-7px)}}
.hop{transform-origin:50% 100%}
@keyframes hop{0%{transform:translateY(0) scale(1,1)}35%{transform:translateY(-16px) scale(.99,1.02)}100%{transform:translateY(0) scale(1,1)}}
.blink{transform-box:fill-box;transform-origin:50% 50%;animation:blink 3.6s linear infinite}
@keyframes blink{0%,91%,100%{transform:scaleY(1)}94%{transform:scaleY(.08)}}
.flap{transform-box:fill-box;transform-origin:50% 30%;animation:flap .17s ease-in-out infinite alternate}
@keyframes flap{from{transform:scaleY(.3)}to{transform:scaleY(1.05)}}
.wave{animation:wave .5s ease-in-out infinite alternate}
@keyframes wave{from{transform:rotate(-14deg)}to{transform:rotate(16deg)}}
.glow{animation:glow 1.2s ease-in-out infinite alternate}
@keyframes glow{from{opacity:.75}to{opacity:1}}
.steam{animation:steam 1.6s ease-in-out infinite;opacity:.6}
.steam.s2{animation-delay:.7s}
@keyframes steam{0%{transform:translateY(10px);opacity:0}40%{opacity:.7}100%{transform:translateY(-50px);opacity:0}}
.sway{animation:sway 2.4s ease-in-out infinite alternate}
@keyframes sway{from{transform:rotate(-5deg)}to{transform:rotate(6deg)}}
.swing{animation:swing 2s ease-in-out infinite alternate}
@keyframes swing{from{transform:rotate(-4deg)}to{transform:rotate(4deg)}}
.fan{transform-box:fill-box;transform-origin:50% 50%;animation:fanb .36s linear infinite}
.fan.f2{animation-delay:-.18s}
@keyframes fanb{0%{transform:scaleX(1)}50%{transform:scaleX(.08)}100%{transform:scaleX(1)}}
.hand{animation:clock 6s linear infinite}
@keyframes clock{from{transform:rotate(0)}to{transform:rotate(360deg)}}
.flame{transform-box:fill-box;transform-origin:50% 100%;animation:flame .35s ease-in-out infinite alternate}
@keyframes flame{from{transform:scale(1,1)}to{transform:scale(.88,1.12)}}
.bus{animation:bus var(--dur) linear both}
@keyframes bus{from{transform:translateX(0)}to{transform:translateX(-1500px)}}
.road{animation:road .6s linear infinite}
@keyframes road{from{transform:translateX(0)}to{transform:translateX(-260px)}}
.tw{animation:tw 1.8s ease-in-out infinite alternate}
@keyframes tw{from{opacity:.25}to{opacity:1}}
.bulb{animation:tw .9s ease-in-out infinite alternate}
@keyframes on{to{opacity:1}}
@keyframes off{to{opacity:0}}
@keyframes shake{0%,100%{transform:translate(0,0)}15%{transform:translate(-18px,8px)}30%{transform:translate(16px,-10px)}
  45%{transform:translate(-12px,-6px)}60%{transform:translate(10px,8px)}80%{transform:translate(-5px,3px)}}
.stage{position:absolute;left:LEFTpx;top:TOPpx;width:STAGEWpx;height:STAGEHpx;z-index:5}
.bub{position:absolute;left:0;right:0;top:0;display:flex;justify-content:center}
.bubble{position:relative;max-width:880px;background:#fff;border:7px solid #1E140E;border-radius:46px;padding:22px 40px 14px;
  font-weight:800;font-size:76px;line-height:1.08;text-align:center;box-shadow:10px 12px 0 rgba(30,20,14,.85);
  transform-origin:50% 100%;animation:pop .34s cubic-bezier(.2,1.6,.4,1) both}
.bubble .tail{position:absolute;bottom:-46px;width:56px;height:56px;background:#fff;border-right:7px solid #1E140E;border-bottom:7px solid #1E140E;
  transform:rotate(45deg) skew(12deg,12deg)}
.caption{position:relative;max-width:900px;background:#FFD23F;border:7px solid #1E140E;padding:16px 34px 8px;font-weight:800;font-size:70px;
  line-height:1.08;text-align:center;transform:rotate(-1.5deg);box-shadow:10px 10px 0 #1E140E;animation:slide .32s cubic-bezier(.2,1.4,.4,1) both}
.big{font-weight:800;font-size:128px;line-height:1.0;text-align:center;color:#fff;-webkit-text-stroke:14px #1E140E;paint-order:stroke fill;
  text-shadow:0 12px 0 #1E140E;animation:slam .3s cubic-bezier(.2,1.5,.4,1) both}
.big.f0{animation:none}
.tag{display:inline-block;max-width:900px;font-weight:800;font-size:66px;line-height:1.08;color:#1E140E;background:#7CE0C3;border:7px solid #1E140E;padding:14px 32px 6px;
  transform:rotate(1.5deg);box-shadow:10px 10px 0 #1E140E;animation:slide .32s cubic-bezier(.2,1.4,.4,1) both;text-align:center}
@keyframes pop{from{transform:scale(.5);opacity:0}to{transform:scale(1);opacity:1}}
@keyframes slide{from{transform:translateY(-40px) rotate(-1.5deg);opacity:0}to{transform:translateY(0) rotate(-1.5deg);opacity:1}}
@keyframes slam{from{transform:scale(1.6);opacity:0}to{transform:scale(1);opacity:1}}
.ans{position:absolute;left:0;right:0;top:0;display:flex;flex-direction:column;align-items:center;gap:10px}
.ans .k{font-weight:800;font-size:54px;letter-spacing:6px;color:#1E140E;background:#FFD23F;padding:6px 26px 0;border:6px solid #1E140E;transform:rotate(-3deg)}
.ans .t{font-weight:800;font-size:112px;line-height:1.0;color:#FFD23F;background:#1E140E;padding:24px 44px 12px;border-radius:24px;text-align:center;
  transform:rotate(-2deg);box-shadow:0 16px 0 rgba(0,0,0,.35);max-width:900px}
.ans .s{font-weight:800;font-size:56px;color:#fff;background:#C2185B;padding:8px 26px 0;border-radius:16px;transform:rotate(1.5deg)}
.ans>*{animation:slam .34s cubic-bezier(.2,1.5,.4,1) both}
.flash{position:absolute;inset:0;background:#fff;opacity:0;z-index:9;animation:flash .45s ease-out both}
@keyframes flash{0%{opacity:.9}100%{opacity:0}}
.sign{position:absolute;left:0;right:0;top:-60px;display:flex;flex-direction:column;align-items:center;transform-origin:50% -200px;
  animation:sign 1.1s cubic-bezier(.3,1.5,.5,1) both}
.sign .ropes{width:560px;height:150px;border-left:6px solid #3B2614;border-right:6px solid #3B2614;margin-bottom:-6px}
.sign .board{background:#7A4A24;border:10px solid #4E2E14;border-radius:22px;padding:26px 46px 16px;font-weight:800;font-size:96px;color:#FFF1C9;
  box-shadow:0 18px 0 rgba(0,0,0,.35);white-space:nowrap}
@keyframes sign{0%{transform:translateY(-700px) rotate(0)}55%{transform:translateY(0) rotate(5deg)}75%{transform:rotate(-3deg)}100%{transform:rotate(0)}}
.fx{position:absolute;pointer-events:none}
.fx.sweat{width:40px;height:56px;background:#7FD3FF;border-radius:50% 50% 50% 50%/60% 60% 40% 40%;border:5px solid #1E140E;animation:sweat 1s ease-in both}
@keyframes sweat{from{transform:translateY(-20px);opacity:0}30%{opacity:1}to{transform:translateY(60px);opacity:0}}
.fx.q{font-weight:800;font-size:110px;color:#fff;-webkit-text-stroke:10px #1E140E;paint-order:stroke fill;animation:q 1.3s ease-out both}
@keyframes q{from{transform:translateY(30px) scale(.4);opacity:0}30%{opacity:1;transform:translateY(0) scale(1)}to{transform:translateY(-80px) scale(1);opacity:0}}
.fx.bulb{animation:pop .35s cubic-bezier(.2,1.6,.4,1) both}
.fx.spark{animation:spark 1s ease-out both}
@keyframes spark{from{transform:scale(.2) rotate(0);opacity:0}30%{opacity:1}to{transform:scale(1.2) rotate(40deg);opacity:0}}
.fx.steamfx{animation:steam 1s ease-out both}
.fx.hearts{animation:q 1.4s ease-out both}
.fx.lines{animation:spark .7s ease-out both}
.phone{position:absolute;left:130px;top:262px;width:820px;height:1760px;background:#15171C;border-radius:74px;padding:26px;
  box-shadow:0 40px 80px rgba(0,0,0,.5);animation:rise .5s cubic-bezier(.2,1.2,.4,1) both}
@keyframes rise{from{transform:translateY(500px) rotate(6deg)}to{transform:translateY(0) rotate(0)}}
.phone .scr{position:relative;width:768px;height:1708px;border-radius:50px;overflow:hidden;background:#F6EFE0}
.phone .scr img{position:absolute;transform-origin:0 0}
.phone .notch{position:absolute;left:50%;top:12px;width:24px;height:24px;margin-left:-12px;background:#15171C;border-radius:50%;z-index:2}
.handsvg{position:absolute;left:0;top:0;width:1080px;height:1920px;animation:rise .5s cubic-bezier(.2,1.2,.4,1) both}
.chips{position:absolute;left:24px;right:24px;bottom:28px;display:flex;flex-direction:column;gap:12px;align-items:stretch}
.chip{font-weight:800;font-size:52px;line-height:1.05;color:#fff;background:rgba(20,22,28,.92);border-left:14px solid #FFD23F;padding:14px 22px 6px;
  border-radius:14px;animation:chipin .3s cubic-bezier(.2,1.4,.4,1) both}
@keyframes chipin{from{transform:translateX(-80px);opacity:0}to{transform:translateX(0);opacity:1}}
.chips.game{gap:18px}
.chips.game{left:31px;right:31px;gap:22px}
.chips.game .row{display:flex;align-items:center;gap:26px;height:100px;background:#FFFBF0;border:3px solid var(--acc);border-bottom-width:6px;border-radius:18px;
  padding:4px 28px 0;font-family:Inter,Arial,sans-serif;font-weight:800;font-size:44px;color:#2A2118;animation:chipin .3s cubic-bezier(.2,1.4,.4,1) both;
  box-shadow:0 0 0 6px rgba(255,210,63,.0)}
.chips.game .row i{font-style:normal;display:inline-flex;align-items:center;justify-content:center;width:58px;height:58px;border:3px solid var(--acc);
  border-radius:50%;font-size:30px;margin-top:-6px}
.ring{position:absolute;right:26px;top:26px;width:170px;height:170px;z-index:3}
.ring circle.run{animation:drain var(--len) linear both}
@keyframes drain{from{stroke-dashoffset:0}to{stroke-dashoffset:500}}
.ring .num{font-weight:800;font-size:84px}
"""
CSS = (CSS.replace("LEFTpx", f"{SAFE['left'] + PAD}px").replace("TOPpx", f"{SAFE['top'] + PAD}px")
       .replace("STAGEWpx", f"{STAGE_W}px").replace("STAGEHpx", f"{SAFE['bottom'] - SAFE['top'] - 2 * PAD}px"))


# ------------------------------------------------------------------------------------------------ scene logic
def _layout(cast, head_y=None):
    n = len(cast)
    head_y = head_y or HEAD_Y
    default_x = {1: [540], 2: [300, 770], 3: [205, 535, 850]}.get(n, [180 + 720 * k / max(1, n - 1) for k in range(n)])
    out = []
    for k, m in enumerate(cast):
        cid = m["id"]
        if cid not in CAST:
            raise SystemExit(f"story theme: unknown cast id '{cid}' (use {', '.join(CAST)})")
        sc = float(m.get("scale", {1: 1.05, 2: 0.98}.get(n, 0.88))) * CAST[cid]["scale"]
        x = float(m.get("x", default_x[k]))
        out.append(dict(m, x=x, sc=sc, hy=head_y + (1.0 - CAST[cid]["scale"]) * 120 * sc,
                        flip=m.get("flip", x > 600)))
    return out


def _cam_tf(cam, cast):
    pos = {m["id"]: m for m in cast}
    if not cam or cam == "wide":
        return (1.0, 0.0, 0.0)
    if cam.startswith("two:"):
        ids = [i.strip() for i in cam[4:].split(",") if i.strip() in pos]
        if len(ids) >= 2:
            xs = [pos[i]["x"] for i in ids]
            hy = sum(pos[i]["hy"] for i in ids) / len(ids)
            z = min(1.45, 820 / (abs(xs[0] - xs[-1]) + 300))
            cx = sum(xs) / len(xs)
            return (z, 540 - z * cx, CLOSE[1] - z * hy)
        cam = ids[0] if ids else "wide"
    if cam in pos:
        z = 1.62
        return (z, CLOSE[0] - z * pos[cam]["x"], CLOSE[1] - z * pos[cam]["hy"])
    return (1.0, 0.0, 0.0)


def _cam_css(name, ts, beats, cast, dur):
    """Keyframes for the camera: each beat's cam holds until the next change, with a 0.4 s ease between."""
    stops = []
    cur = None
    for b, t in zip(beats, ts):
        if "cam" in b or cur is None:
            tf = _cam_tf(b.get("cam", "wide") if "cam" in b else "wide", cast)
            if cur is None:
                stops.append((0.0, tf))
            elif tf != cur:
                stops.append((max(0.0, t - 0.02), cur))
                stops.append((min(dur, t + 0.38), tf))
            cur = tf
    stops.append((dur, cur))
    rule = lambda tf: f"transform:translate({tf[1]:.1f}px,{tf[2]:.1f}px) scale({tf[0]:.3f})"
    frames = "".join(f"{100 * t / dur:.3f}%{{{rule(tf)};animation-timing-function:ease-in-out}}" for t, tf in stops)
    return f"@keyframes {name}{{{frames}}}", stops


def _screen_pos(stops, t, x, y):
    tf = stops[0][1]
    for st, f in stops:
        if st <= t + 0.4:
            tf = f
    return tf[0] * x + tf[1], tf[0] * y + tf[2]


def _segments(m, beats, ts, dur):
    mood, pose = m.get("mood", "normal"), m.get("pose", "down")
    segs, start = [], 0.0
    for b, t in zip(beats, ts):
        nm = (b.get("mood") or {}).get(m["id"], mood)
        np_ = (b.get("pose") or {}).get(m["id"], pose)
        if (nm, np_) != (mood, pose):
            segs.append((start, t, mood, pose))
            start, mood, pose = t, nm, np_
    segs.append((start, None, mood, pose))
    return segs


def _fx_html(kind, x, y, t, sc):
    s = sc
    if kind == "sweat":
        return f'<div class="fx sweat" style="left:{x + 80 * s:.0f}px;top:{y - 70 * s:.0f}px;{d(t)}"></div>'
    if kind == "qmarks":
        return "".join(f'<div class="fx q" style="left:{x + dx * s:.0f}px;top:{y - 230 * s + dy:.0f}px;{d(t + k * 0.18)}">?</div>'
                       for k, (dx, dy) in enumerate(((-110, 0), (40, -40), (150, 10))))
    if kind == "bulb":
        return (f'<svg class="fx bulb" style="left:{x - 50:.0f}px;top:{y - 290 * s:.0f}px;width:100px;height:140px;{d(t)}" viewBox="0 0 100 140">'
                '<circle cx="50" cy="50" r="40" fill="#FFE45C" stroke="#1E140E" stroke-width="6"/><rect x="32" y="88" width="36" height="30" rx="6" fill="#9AA3AD" stroke="#1E140E" stroke-width="6"/>'
                '<path d="M50 -4 L50 -24 M0 20 L-16 8 M100 20 L116 8" stroke="#FFE45C" stroke-width="8" stroke-linecap="round"/></svg>')
    if kind == "spark":
        star = '<path d="M30 0 L37 23 L60 30 L37 37 L30 60 L23 37 L0 30 L23 23 Z" fill="#FFE45C" stroke="#1E140E" stroke-width="4"/>'
        return "".join(f'<svg class="fx spark" style="left:{x + dx * s:.0f}px;top:{y + dy * s:.0f}px;width:60px;height:60px;{d(t + 0.1 * k)}" viewBox="0 0 60 60">{star}</svg>'
                       for k, (dx, dy) in enumerate(((-170, -150), (120, -190), (150, 20), (-190, 10))))
    if kind == "steam":
        puff = '<circle cx="30" cy="30" r="26" fill="#fff" stroke="#1E140E" stroke-width="5"/>'
        return "".join(f'<svg class="fx steamfx" style="left:{x + dx * s:.0f}px;top:{y - 40 * s:.0f}px;width:60px;height:60px;{d(t + 0.15 * k)}" viewBox="0 0 60 60">{puff}</svg>'
                       for k, dx in enumerate((-150, 110, -150, 110)))
    if kind == "hearts":
        return "".join(f'<div class="fx q" style="left:{x + dx * s:.0f}px;top:{y - 220 * s:.0f}px;color:#FF4D6D;{d(t + 0.2 * k)}">♥</div>'
                       for k, dx in enumerate((-90, 60)))
    if kind == "lines":
        ln = "".join(f'<path d="M{60 + 50 * math.cos(a):.1f} {60 + 50 * math.sin(a):.1f} L{60 + 80 * math.cos(a):.1f} {60 + 80 * math.sin(a):.1f}" stroke="#1E140E" stroke-width="8" stroke-linecap="round"/>'
                     for a in (3.6, 4.2, 4.7, 5.2, 5.8))
        return f'<svg class="fx lines" style="left:{x - 160 * s:.0f}px;top:{y - 220 * s:.0f}px;width:{320 * s:.0f}px;height:{240 * s:.0f}px;{d(t)}" viewBox="0 0 120 90">{ln}</svg>'
    return ""


def _text_layer(beats, ts, dur, first_scene, stops, cast_pos, kind_default="bubble"):
    """Bubbles, captions, big lines, tags. Each text beat replaces the one before it; an answer, URL sign or echo
    beat clears the text. pos: top (default), mid, low."""
    events = [t for b, t in zip(beats, ts) if b.get("text") or b.get("answer") or b.get("url") or b.get("echo")]
    items = [(b, t) for b, t in zip(beats, ts) if b.get("text") and not b.get("url") and not b.get("echo")]
    out = []
    for k, (b, t) in enumerate(items):
        end = next((e for e in events if e > t + 0.001), None)
        style = b.get("style") or ("caption" if b.get("speaker") in (None, "narrator") else kind_default)
        frame0 = first_scene and k == 0 and t < 0.05
        txt = esc(b["text"])
        if style == "big":
            inner = f'<div class="big{" f0" if frame0 else ""}" style="{d(t)}">{txt}</div>'
        elif style == "tag":
            inner = f'<div class="tag" style="{d(t)}">{txt}</div>'
        elif style == "caption":
            inner = f'<div class="caption" style="{d(t)}">{txt}</div>'
        else:
            m = cast_pos.get(b.get("speaker"))
            tail = ""
            if m:
                sx, _ = _screen_pos(stops, t, m["x"], m["hy"])
                tail = f'<div class="tail" data-tx="{sx - SAFE["left"] - PAD:.0f}"></div>'
            inner = f'<div class="bubble" style="{d(t)}">{txt}{tail}</div>'
        top = {"mid": 300, "low": 690}.get(b.get("pos") or ("mid" if style == "tag" else "top"), 0)
        vis = win(0 if frame0 else t, end)
        out.append(f'<div class="bub" style="top:{top}px;{vis}">{inner}</div>')
    return "".join(out)


BUB_JS = """<script>
document.querySelectorAll('.bubble .tail').forEach(t => {
  const b = t.parentElement, st = b.closest('.stage').getBoundingClientRect();
  const want = parseFloat(t.dataset.tx), bx = b.getBoundingClientRect().left - st.left;
  t.style.left = Math.max(40, Math.min(b.offsetWidth - 100, want - bx - 28)) + 'px'; });
</script>"""


def _scene_world(s, ts, dur, beats, cast, cam_name):
    setting = s.get("setting", "living-room")
    lens = s.get("_lens") or [0] * len(beats)
    cam_css, stops = _cam_css(cam_name, ts, beats, cast, dur)
    chars = []
    for k, m in enumerate(cast):
        talks = [(t, t + max(0.2, ln)) for b, t, ln in zip(beats, ts, lens) if b.get("speaker") == m["id"] and b.get("say") and ln > 0]
        segs = _segments(m, beats, ts, dur)
        svg = character(m["id"], segs, talks, (0.9 * k + 0.4) % 3.6)
        w, h = 400 * m["sc"], 1150 * m["sc"]
        left, top = m["x"] - LOCAL_HEAD[0] * m["sc"], m["hy"] - LOCAL_HEAD[1] * m["sc"]
        hops = ",".join(f"hop .34s ease-out {a:.3f}s" for a, _ in talks)
        flip = "transform:scaleX(-1);" if m["flip"] else ""
        chars.append(f'<div class="char idle" style="left:{left:.0f}px;top:{top:.0f}px;width:{w:.0f}px;height:{h:.0f}px;animation-delay:-{0.5 * k:.2f}s">'
                     f'<div class="hop" style="width:100%;height:100%;{("animation:" + hops) if hops else ""}">'
                     f'<svg viewBox="-60 -40 520 1190" style="position:absolute;left:{-60 * m["sc"]:.0f}px;top:{-40 * m["sc"]:.0f}px;width:{520 * m["sc"]:.0f}px;height:{1190 * m["sc"]:.0f}px;{flip}overflow:visible">{svg}</svg>'
                     f'</div></div>')
    pos = {m["id"]: m for m in cast}
    fx = []
    for b, t in zip(beats, ts):
        for kind in ([b["fx"]] if isinstance(b.get("fx"), str) else (b.get("fx") or [])):
            if kind == "shake":
                continue
            who = pos.get(b.get("on") or b.get("speaker")) or (cast[0] if cast else None)
            if who:
                fx.append(_fx_html(kind, who["x"], who["hy"], t, who["sc"]))
    shakes = ",".join(f"shake .5s linear {t:.3f}s" for b, t in zip(beats, ts)
                      if b.get("fx") == "shake" or (isinstance(b.get("fx"), list) and "shake" in b["fx"]))
    tint = f'<div class="tint" style="background:{TINTS[s["tint"]]}"></div>' if s.get("tint") in TINTS else ""
    world = (f'<div class="shk" style="{("animation:" + shakes) if shakes else ""}"><div class="drift">'
             f'<div class="cam" style="animation:{cam_name} {dur:.3f}s linear both">'
             f'<svg class="bgsvg" viewBox="0 0 1080 1920" preserveAspectRatio="xMidYMid slice">{setting_svg(setting)}</svg>'
             f'{"".join(chars)}{"".join(fx)}</div></div>{tint}</div>')
    return world, cam_css, stops, pos


def _answer(b, t, end=None):
    a = b.get("answer") or {}
    k = f'<div class="k" style="{d(t)}">{esc(a.get("kicker", "ANSWER"))}</div>'
    tt = f'<div class="t" style="{d(t + 0.08)}">{esc(a.get("title", ""))}</div>'
    sub = f'<div class="s" style="{d(t + 0.22)}">{esc(a["sub"])}</div>' if a.get("sub") else ""
    return f'<div class="ans" style="{win(t, end)}">{k}{tt}{sub}</div>', f'<div class="flash" style="{d(t)}"></div>'


HAND_BACK = ('<svg class="handsvg" viewBox="0 0 1080 1920"><path d="M40 1920 L70 1420 Q84 1340 170 1330 L250 1340 L250 1920 Z" fill="SKIN"/>'
             '<path d="M1040 1920 L1010 1420 Q996 1340 910 1330 L830 1340 L830 1920 Z" fill="SKIN"/>'
             '<path d="M-40 1720 L300 1760 L320 1960 L-40 1960 Z" fill="SLEEVE"/><path d="M1120 1720 L780 1760 L760 1960 L1120 1960 Z" fill="SLEEVE"/></svg>')
HAND_FRONT = ('<svg class="handsvg" viewBox="0 0 1080 1920">'
              + "".join(f'<rect x="104" y="{1350 + 78 * k}" width="62" height="66" rx="30" fill="SKIN" stroke="SHADE" stroke-width="4"/>'
                        f'<rect x="914" y="{1350 + 78 * k}" width="62" height="66" rx="30" fill="SKIN" stroke="SHADE" stroke-width="4"/>' for k in range(3))
              + '<rect x="150" y="1540" width="74" height="210" rx="37" fill="SKIN" stroke="SHADE" stroke-width="4" transform="rotate(-28 187 1645)"/>'
              '<rect x="856" y="1540" width="74" height="210" rx="37" fill="SKIN" stroke="SHADE" stroke-width="4" transform="rotate(28 893 1645)"/></svg>')


def _phone(s, ts, dur, spec_dir):
    beats = s["beats"]
    who = CAST.get(s.get("holder", "appu"), CAST["appu"])
    shot = s.get("shot")
    img = ""
    if shot:
        p = (pathlib.Path(spec_dir) / shot).resolve()
        if not p.exists():
            raise SystemExit(f"story phone scene: missing screenshot {p}")
        from PIL import Image
        iw, ih = Image.open(p).size
        cx, cy, cw, ch = s.get("crop") or [0, 0, iw, ih]
        z = 768 / cw
        img = (f'<img src="file://{p}" style="left:{-cx * z:.0f}px;top:{-cy * z:.0f}px;width:{iw * z:.0f}px;height:{ih * z:.0f}px;'
               f'animation:scr {dur:.2f}s linear both">')
    chips, timers = [], []
    n = int(s.get("chipStart", 1))
    game_rows = s.get("chipStyle") == "game"
    for b, t in zip(beats, ts):
        if b.get("chip"):
            if game_rows:
                chips.append(f'<div class="row" style="{d(t)}"><i>{n}</i>{esc(b["chip"])}</div>')
            else:
                chips.append(f'<div class="chip" style="{d(t)}">{esc(b["chip"])}</div>')
            n += 1
        if b.get("timer"):
            n = float(b["timer"])
            nums = "".join(f'<text class="num" x="85" y="112" text-anchor="middle" fill="#1E140E" style="{win(t + j, t + j + 1 if j < int(n) - 1 else None)}">{int(n) - j}</text>'
                           for j in range(int(n)))
            timers.append(f'<svg class="ring" style="{win(t, t + n + 0.3)};--len:{n:.2f}s" viewBox="0 0 170 170"><circle cx="85" cy="85" r="78" fill="#FFD23F" stroke="#1E140E" stroke-width="8"/>'
                          f'<circle class="run" cx="85" cy="85" r="66" fill="none" stroke="#1E140E" stroke-width="14" stroke-dasharray="415 500" '
                          f'transform="rotate(-90 85 85)" style="{d(t)}"/>{nums}</svg>')
    paint = lambda h: h.replace("SKIN", who["skin"]).replace("SHADE", who["shade"]).replace("SLEEVE", who["sleeve"])
    phone = (f'{paint(HAND_BACK)}<div class="phone"><div class="scr"><div class="notch"></div>{img}{"".join(timers)}'
             f'<div class="chips{" game" if game_rows else ""}" style="{("top:%dpx;bottom:auto;--acc:%s" % (int(s["chipTop"]), s.get("accent", "#C29B2A"))) if s.get("chipTop") is not None else ""}">{"".join(chips)}</div></div></div>{paint(HAND_FRONT)}')
    return phone


def scene_html(s, i, gid, ts, dur, start, total, spec_dir, fonts):
    t = s["type"]
    beats = s["beats"]
    cam_name = f"cam{i}"
    over = ""
    if t in ("hook", "shot", "loop"):
        cast = _layout(s.get("cast", []), s.get("headY") or (900 if t == "loop" else None))
        world, cam_css, stops, pos = _scene_world(s, ts, dur, beats, cast, cam_name)
        texts = _text_layer(beats, ts, dur, i == 0, stops, pos)
        extra = ""
        for j, (b, bt) in enumerate(zip(beats, ts)):
            if b.get("answer"):
                nxt = next((t2 for b2, t2 in list(zip(beats, ts))[j + 1:] if b2.get("text") or b2.get("url") or b2.get("echo")), None)
                a, fl = _answer(b, bt, nxt)
                extra += a
                over += fl
            if b.get("url"):
                extra += (f'<div style="{win(bt)}"><div class="sign" style="{d(bt)}"><div class="ropes"></div>'
                          f'<div class="board">{esc(b["text"])}</div></div></div>')
            if b.get("echo"):
                over += (f'<div class="stage" style="z-index:8;{win(bt)}"><div class="bub"><div class="big" style="{d(bt)}">{esc(b["echo"])}</div></div></div>'
                         f'<div style="position:absolute;inset:0;background:rgba(30,20,14,.35);z-index:7;{win(bt)}"></div>')
        echo_t = next((bt for b, bt in zip(beats, ts) if b.get("echo")), None)
        hide = f"animation:off .01s linear {echo_t:.3f}s forwards" if echo_t is not None else ""
        body = f'{world}<div class="stage"><div style="position:absolute;inset:0;{hide}">{texts}{extra}</div></div>'
    elif t == "phone":
        setting = s.get("setting", "living-room")
        cam_css = ""
        bg = (f'<svg class="bgsvg" viewBox="0 0 1080 1920" style="filter:blur(16px) brightness(.55) saturate(1.2);transform:scale(1.15)">'
              f'{setting_svg(setting)}</svg>')
        phone = _phone(s, ts, dur, spec_dir)
        for b in beats:
            if b.get("text") and "pos" not in b:
                b["pos"] = "low"
        texts = _text_layer(beats, ts, dur, i == 0, [(0, (1, 0, 0))], {}, "caption")
        for b, bt in zip(beats, ts):
            if b.get("answer"):
                a, fl = _answer(b, bt)
                texts += a
                over += fl
        body = (f'<div class="drift">{bg}</div><div class="drift" style="animation-name:push2">{phone}</div>'
                f'<div class="stage">{texts}</div>')
        cam_css = ("@keyframes push2{from{transform:scale(1)}to{transform:scale(1.06)}}"
                   f"@keyframes scr{{from{{transform:translateY(0)}}to{{transform:translateY(-{float(s.get('scroll', 0)):.0f}px)}}}}")
    else:
        raise SystemExit(f"Scene type '{t}' is not in the story theme (hook, shot, phone, loop)")
    # NB: no lang="ml" on <html> (it splits conjuncts in Baloo Chettan 2).
    return (f'<!doctype html><html><head><meta charset="utf-8">{fonts}<style>{CSS}{cam_css}</style></head><body>'
            f'<div class="reel" style="--dur:{dur:.2f}s">{body}{over}</div>{BUB_JS}</body></html>')
