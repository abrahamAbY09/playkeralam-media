"""Check a finished post or reel folder before it is scheduled. Exit code 1 if anything fails.

    python3 check.py FOLDER

FOLDER holds either slide-N.jpg files (a post) or reel.mp4 (a reel), plus caption.txt and, for posts,
alt.json (one alt text per slide). It checks sizes and formats, the 5-hashtag limit, caption length,
the brand rules (Play Keralam / playkeralam.com, never the old name or address) and the link line.
"""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import CONFIG  # noqa: E402
from PIL import Image  # noqa: E402

folder = pathlib.Path(sys.argv[1])
errors, notes = [], []

caption_file = folder / "caption.txt"
if not caption_file.exists():
    errors.append("caption.txt is missing")
    caption = ""
else:
    caption = caption_file.read_text(encoding="utf-8").strip()
tags = re.findall(r"(?<!\w)#[\wഀ-ൿ]+", caption)
if len(tags) > CONFIG["captions"]["maxHashtags"]:
    numeric = [t for t in tags if re.fullmatch(r"#\d+", t)]
    hint = f" ({', '.join(numeric)} counts as a hashtag; write 'നമ്പർ N' instead of '#N' in the caption)" if numeric else ""
    errors.append(f"{len(tags)} hashtags; Instagram allows {CONFIG['captions']['maxHashtags']}{hint}")
if CONFIG["captions"]["alwaysTag"] not in tags:
    errors.append(f"caption lacks {CONFIG['captions']['alwaysTag']}")
if len(caption) > 2200:
    errors.append(f"caption is {len(caption)} characters; Instagram allows 2,200")
if "Link in bio" not in caption and "ലിങ്ക് ബയോയിൽ" not in caption:
    errors.append("caption lacks the 'Link in bio' line")
for bad in CONFIG["brand"]["never_say"]:
    if bad.lower() in caption.lower():
        errors.append(f"caption mentions '{bad}' (use Play Keralam / playkeralam.com)")

slides = sorted(folder.glob("slide-*.jpg"), key=lambda p: int(re.findall(r"\d+", p.name)[0]))
reel = folder / "reel.mp4"
if slides:
    for s in slides:
        im = Image.open(s)
        if im.format != "JPEG" or im.size != (CONFIG["posts"]["width"], CONFIG["posts"]["height"]):
            errors.append(f"{s.name}: {im.format} {im.size}; need JPEG {CONFIG['posts']['width']}x{CONFIG['posts']['height']}")
    if not 1 <= len(slides) <= 10:
        errors.append(f"{len(slides)} slides; Instagram carousels take 1-10")
    alt = folder / "alt.json"
    if not alt.exists():
        errors.append("alt.json is missing")
    elif len(json.loads(alt.read_text(encoding="utf-8"))) != len(slides):
        errors.append("alt.json needs one alt text per slide")
    notes.append(f"post: {len(slides)} slides")
elif reel.exists():
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate",
                                       "-of", "json", str(reel)], capture_output=True, text=True, check=True).stdout)
    v = next(s for s in probe["streams"] if s["codec_type"] == "video")
    a = [s for s in probe["streams"] if s["codec_type"] == "audio"]
    dur = float(probe["format"]["duration"])
    if v["codec_name"] != "h264" or (v["width"], v["height"]) != (1080, 1920):
        errors.append(f"video is {v['codec_name']} {v['width']}x{v['height']}; need h264 1080x1920")
    if not a or a[0]["codec_name"] != "aac":
        errors.append("reel needs an AAC audio track")
    if not 3 <= dur <= 90:
        errors.append(f"reel is {dur:.1f}s; Instagram needs 3-90s")
    lo, hi = CONFIG["reels"]["minSeconds"], CONFIG["reels"]["maxSeconds"]
    if not lo - 2 <= dur <= hi + 4:
        notes.append(f"reel is {dur:.1f}s; the plan aims for {lo}-{hi}s")
    if int(probe["format"]["size"]) > 100 * 1024 * 1024:
        errors.append("reel is over 100 MB")
    notes.append(f"reel: {dur:.1f}s")
else:
    errors.append("no slide-*.jpg and no reel.mp4")

for n in notes:
    print("ok:", n)
print(f"ok: {len(tags)} hashtags, caption {len(caption)} characters")
for e in errors:
    print("FAIL:", e)
sys.exit(1 if errors else 0)
