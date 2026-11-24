"""ElevenLabs voice lines for a reel, voiced ONCE and kept in the repo (Abr, 25 Nov 2026: the free plan has a small
monthly credit pool, 1 credit per character, so nothing may be voiced twice).

    python3 voice_lines.py plan spec.json            # every line: speaker, voice, characters, cached or not; budget check
    python3 voice_lines.py put spec.json N FILE      # store ElevenLabs audio FILE as line N (from `plan`) and log its credits
    python3 voice_lines.py usage                     # credits used this cycle (from automation/voice-usage.json)

How a reel is voiced (playbook step 3):
  1. Freeze the script first: every "say" line final, facts checked. Changing a line after it is voiced costs again.
  2. `plan` lists the lines. Voice ONLY the ones marked "voice": the others are already in the cache (same text, voice,
     model and settings), so they cost nothing. If `plan` exits 2 the reel is over budget: shorten lines first.
  3. Voice each listed line exactly once with the ElevenLabs connector (model, voice id and language from `plan`),
     then `put` the file at once. Never re-voice a line to "try again"; if a take is unusable, say so in the summary.
  4. Commit and push automation/voice-cache/ and automation/voice-usage.json right after voicing, before rendering,
     so a later failure can't lose audio that was paid for.
The renderer reads only the cache and never calls ElevenLabs, so re-renders are free.
"""
import datetime as dt
import json
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import AUTOMATION, CONFIG  # noqa: E402
from voice import VOICE_CACHE, eleven_cfg, eleven_voice, line_key  # noqa: E402

USAGE = AUTOMATION / "voice-usage.json"


def clean(text):
    return str(text or "").replace("‌", "").strip()


def lines(spec):
    out = []
    for si, s in enumerate(spec["scenes"]):
        for b in s["beats"]:
            if b.get("say"):
                text = clean(b["say"])
                speaker = b.get("speaker") or "narrator"
                vid = eleven_voice(speaker)
                key = line_key(text, vid)
                out.append(dict(n=len(out), scene=si + 1, speaker=speaker, voiceId=vid, text=text, chars=len(text),
                                key=key, file=str(VOICE_CACHE / f"{key}.mp3"), cached=(VOICE_CACHE / f"{key}.mp3").exists()))
    return out


def load_usage():
    if USAGE.exists():
        return json.loads(USAGE.read_text(encoding="utf-8"))
    return {"_about": "Every ElevenLabs line voiced for a reel (1 credit per character). Written by voice_lines.py put.",
            "entries": []}


def cycle_start(today=None):
    """Start of the current credit cycle: the plan's reset day (config voice.eleven.cycleStartDay), else the 1st."""
    today = today or dt.date.today()
    day = int(eleven_cfg().get("cycleStartDay") or 1)
    start = today.replace(day=min(day, 28))
    if start > today:
        prev = (today.replace(day=1) - dt.timedelta(days=1))
        start = prev.replace(day=min(day, 28))
    return start


def used_this_cycle(usage=None):
    usage = usage or load_usage()
    start = cycle_start().isoformat()
    return sum(e["chars"] for e in usage["entries"] if e["date"] >= start)


def cmd_plan(spec_path):
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    cfg = eleven_cfg()
    ls = lines(spec)
    need = [x for x in ls if not x["cached"]]
    cost = sum(x["chars"] for x in need)
    total = sum(x["chars"] for x in ls)
    used = used_this_cycle()
    pool = int(cfg.get("monthlyCredits", 10000))
    left = pool - used
    cap = int(cfg.get("maxCharsPerReel", 450))
    reserve = int(cfg.get("reserve", 300))
    for x in ls:
        state = "cached (free)" if x["cached"] else "VOICE"
        print(f'{x["n"]:>2}  {state:<13} {x["speaker"]:<9} {x["chars"]:>3} ch  {x["text"]}')
    print(f"\nmodel {cfg.get('model', 'eleven_v3')}, language {cfg.get('languageCode', 'ml')}, settings {json.dumps(cfg.get('settings', {}))}")
    print(f"script {total} characters (cap {cap}); to voice now {len(need)} lines = {cost} credits; "
          f"used this cycle {used} of {pool} (from {cycle_start()}); left after this reel {left - cost}")
    print(json.dumps({"voice": [{k: x[k] for k in ("n", "speaker", "voiceId", "text", "chars", "file")} for x in need],
                      "cost": cost, "scriptChars": total, "usedThisCycle": used, "pool": pool}, ensure_ascii=False))
    if total > cap:
        print(f"OVER BUDGET: the script is {total} characters; cut it to {cap} or less before voicing.")
        sys.exit(2)
    if cost > left - reserve:
        print(f"NOT ENOUGH CREDITS: {left} left this cycle, {reserve} kept in reserve. Render with \"voiceProvider\": \"piper\" "
              "instead and say so in the summary.")
        sys.exit(3)


def cmd_put(spec_path, n, src, folder=""):
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    ls = lines(spec)
    x = ls[int(n)]
    dest = pathlib.Path(x["file"])
    if dest.exists():
        print(f"line {n} is already in the cache ({dest.name}); nothing to do (and it should not have been voiced again)")
        return
    src = pathlib.Path(src)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                           capture_output=True, text=True)
    try:
        seconds = float(probe.stdout.strip())
    except ValueError:
        raise SystemExit(f"{src} is not readable audio: {probe.stderr[:200]}")
    if seconds < 0.2:
        raise SystemExit(f"{src} is only {seconds:.2f}s long; check the take before storing it")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".mp3":
        shutil.copyfile(src, dest)
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-codec:a", "libmp3lame", "-b:a", "128k", str(dest)], check=True)
    usage = load_usage()
    usage["entries"].append({"date": dt.date.today().isoformat(), "reelDate": spec.get("date"), "folder": folder,
                             "speaker": x["speaker"], "voiceId": x["voiceId"], "model": eleven_cfg().get("model", "eleven_v3"),
                             "chars": x["chars"], "key": x["key"], "seconds": round(seconds, 2)})
    USAGE.write_text(json.dumps(usage, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"stored line {n} ({x['chars']} credits, {seconds:.2f}s) as {dest.relative_to(AUTOMATION)}")


def cmd_usage():
    usage = load_usage()
    pool = int(eleven_cfg().get("monthlyCredits", 10000))
    used = used_this_cycle(usage)
    print(f"cycle from {cycle_start()}: {used} of {pool} credits used, {pool - used} left")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["plan"] and len(a) == 2:
        cmd_plan(a[1])
    elif a[:1] == ["put"] and len(a) in (4, 5):
        cmd_put(*a[1:])
    elif a[:1] == ["usage"]:
        cmd_usage()
    else:
        raise SystemExit(__doc__)
