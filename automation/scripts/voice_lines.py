"""ElevenLabs voice lines for a reel, voiced ONCE and kept in the repo (Abr, 24 Nov 2026: the free plan has a small
monthly credit pool, 1 credit per character, so nothing may be voiced twice).

    python3 voice_lines.py preflight                        # free: cast set, and audio can be downloaded here
    python3 voice_lines.py plan spec.json [--left N]        # every line: cached / paid (fetch) / VOICE, and the budget
    python3 voice_lines.py fetch spec.json N URL --flow F --gen G   # download a voiced line and store it as line N
    python3 voice_lines.py put spec.json N FILE [--flow F --gen G]  # store an audio FILE you already have as line N
    python3 voice_lines.py usage                            # credits logged this cycle (voice-usage.json)

How a reel is voiced (playbook step 4; connector details in automation/ELEVENLABS.md):
  0. `preflight` before anything is voiced. If it fails, or the ElevenLabs tools are missing in this session,
     render with "voiceProvider": "piper": a line voiced here that can't be downloaded is wasted credit.
  1. Freeze the script: every "say" line (and its optional "tone" tag) final, facts checked. Changing a line after
     it is voiced costs again.
  2. `plan --left N`, with N = character_limit - character_count from the connector's account_get_usage (the real
     balance). Lines marked "cached" cost nothing. Lines marked "PAID, fetch" were voiced by an earlier run but
     never downloaded: get a fresh URL with creative_get_generations(flow, [gen]) and `fetch` them, never voice them
     again. Voice ONLY the lines marked VOICE. Exit 2 = over the per-reel cap (shorten lines); exit 3 = not enough
     credits (render with Piper).
  3. Voice each VOICE line exactly once (creative_generate_speech, model and voice id from `plan`,
     generations_count 1), then `fetch` it with the URL, flow id and generation id from the run status. `fetch`
     logs the line as paid BEFORE downloading, so a failed download is never voiced twice.
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
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import AUTOMATION  # noqa: E402
from voice import VOICE_CACHE, eleven_cfg, eleven_prompt, eleven_voice, line_key  # noqa: E402

USAGE = AUTOMATION / "voice-usage.json"
CAST = ("ammachi", "uncle", "appu", "meenu", "narrator")
DOWNLOAD_HOST = "elevenlabsusercontent.com"


def clean(text):
    return str(text or "").replace("‌", "").strip()


def today():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()


def load_usage():
    if USAGE.exists():
        return json.loads(USAGE.read_text(encoding="utf-8"))
    return {"_about": "Every ElevenLabs line voiced for a reel (1 credit per character). Written by voice_lines.py: "
                      "status 'pending' = paid but not downloaded yet (fetch it, never voice it again); "
                      "'stored' = in voice-cache/eleven.",
            "entries": []}


def save_usage(usage):
    USAGE.write_text(json.dumps(usage, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def pending_by_key(usage=None):
    usage = usage or load_usage()
    return {e["key"]: e for e in usage["entries"] if e.get("status") == "pending"}


def lines(spec):
    out = []
    pend = pending_by_key()
    for si, s in enumerate(spec["scenes"]):
        for b in s["beats"]:
            if b.get("say"):
                text = clean(b["say"])
                prompt = eleven_prompt(text, b.get("tone"))
                speaker = b.get("speaker") or "narrator"
                vid = eleven_voice(speaker)
                key = line_key(prompt, vid)
                f = VOICE_CACHE / f"{key}.mp3"
                state = "cached" if f.exists() else ("paid" if key in pend else "voice")
                x = dict(n=len(out), scene=si + 1, speaker=speaker, voiceId=vid, text=text, prompt=prompt,
                         chars=len(prompt), key=key, file=str(f), state=state)
                if state == "paid":
                    x.update(flow=pend[key].get("flow"), gen=pend[key].get("gen"))
                out.append(x)
    return out


def cycle_start(day=None):
    """Start of the current credit cycle: the plan's reset day (config voice.eleven.cycleStartDay), else the 1st."""
    day_ = day or today()
    d = int(eleven_cfg().get("cycleStartDay") or 1)
    start = day_.replace(day=min(d, 28))
    if start > day_:
        prev = day_.replace(day=1) - dt.timedelta(days=1)
        start = prev.replace(day=min(d, 28))
    return start


def used_this_cycle(usage=None):
    usage = usage or load_usage()
    start = cycle_start().isoformat()
    return sum(e["chars"] for e in usage["entries"] if e["date"] >= start)


def opt(args, name, default=None):
    if name in args:
        i = args.index(name)
        val = args[i + 1]
        del args[i:i + 2]
        return val
    return default


def cmd_preflight():
    """Free checks before any credit is spent. Exit 0 = ElevenLabs can be used in this run."""
    problems = []
    cast = eleven_cfg().get("cast", {})
    missing = [c for c in CAST if not cast.get(c)]
    if missing:
        problems.append(f"config.json voice.eleven.cast has no voice id for: {', '.join(missing)}")
    r = subprocess.run(["curl", "-sS", "-o", "/dev/null", "--max-time", "20", "-w", "%{http_connect} %{http_code}",
                        f"https://{DOWNLOAD_HOST}/"], capture_output=True, text=True)
    connect, _, code = (r.stdout.strip() + "  ").partition(" ")
    code = code.strip()
    if code in ("", "000"):
        why = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else f"curl exit {r.returncode}"
        problems.append(f"this workspace can't download from {DOWNLOAD_HOST} ({why}). It must be listed in claude.ai "
                        f"Settings > Capabilities > Allowed websites; until then ElevenLabs audio can't reach the repo.")
    for p in problems:
        print("FAIL:", p)
    if problems:
        print("Render with \"voiceProvider\": \"piper\" and say why in the summary. Voice nothing.")
        sys.exit(5)
    print(f"ok: cast set ({', '.join(CAST)}); {DOWNLOAD_HOST} reachable (HTTP {code}); "
          f"model {eleven_cfg().get('model', 'eleven_v3')}")


def cmd_plan(spec_path, args):
    left_arg = opt(args, "--left")
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    cfg = eleven_cfg()
    ls = lines(spec)
    need = [x for x in ls if x["state"] == "voice"]
    paid = [x for x in ls if x["state"] == "paid"]
    cost = sum(x["chars"] for x in need)
    total = sum(x["chars"] for x in ls)
    pool = int(cfg.get("monthlyCredits", 10000))
    if left_arg is not None:
        left, source = int(left_arg), "account_get_usage"
    else:
        left, source = pool - used_this_cycle(), f"voice-usage.json since {cycle_start()} (pass --left for the real balance)"
    cap = int(cfg.get("maxCharsPerReel", 450))
    reserve = int(cfg.get("reserve", 300))
    label = {"cached": "cached (free)", "paid": "PAID, fetch", "voice": "VOICE"}
    for x in ls:
        print(f'{x["n"]:>2}  {label[x["state"]]:<13} {x["speaker"]:<9} {x["chars"]:>3} ch  {x["prompt"]}')
    print(f"\nmodel {cfg.get('model', 'eleven_v3')}, language {cfg.get('languageCode', 'ml')} "
          f"(detected from the Malayalam script), generations_count 1")
    print(f"script {total} characters; to voice now {len(need)} lines = {cost} credits (cap {cap} per reel); "
          f"{len(paid)} paid line(s) to fetch; credits left {left} ({source}); left after this reel {left - cost}")
    print(json.dumps({"voice": [{k: x[k] for k in ("n", "speaker", "voiceId", "prompt", "chars")} for x in need],
                      "fetch": [{k: x[k] for k in ("n", "speaker", "flow", "gen")} for x in paid],
                      "cost": cost, "scriptChars": total, "creditsLeft": left}, ensure_ascii=False))
    if cost > cap:
        print(f"OVER BUDGET: this reel would spend {cost} credits; shorten lines (or drop tone tags) to {cap} or less.")
        sys.exit(2)
    if cost > left - reserve:
        print(f"NOT ENOUGH CREDITS: {left} left, {reserve} kept in reserve. Render with \"voiceProvider\": \"piper\" "
              "instead and say so in the summary.")
        sys.exit(3)


def _log(usage, x, spec, status, flow=None, gen=None, seconds=None, folder=""):
    """Add or update the usage entry for line x (one entry per key, so nothing is counted twice)."""
    for e in usage["entries"]:
        if e.get("key") == x["key"]:
            e["status"] = status
            if flow:
                e["flow"] = flow
            if gen:
                e["gen"] = gen
            if seconds is not None:
                e["seconds"] = round(seconds, 2)
            return e
    e = {"date": today().isoformat(), "reelDate": spec.get("date"), "folder": folder, "speaker": x["speaker"],
         "voiceId": x["voiceId"], "model": eleven_cfg().get("model", "eleven_v3"), "chars": x["chars"],
         "key": x["key"], "prompt": x["prompt"], "status": status, "flow": flow or "", "gen": gen or ""}
    if seconds is not None:
        e["seconds"] = round(seconds, 2)
    usage["entries"].append(e)
    return e


def cmd_put(spec_path, n, src, args):
    flow, gen = opt(args, "--flow"), opt(args, "--gen")
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    x = lines(spec)[int(n)]
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
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-codec:a", "libmp3lame", "-b:a", "192k", str(dest)],
                       check=True)
    usage = load_usage()
    _log(usage, x, spec, "stored", flow, gen, seconds)
    save_usage(usage)
    print(f"stored line {n} ({x['chars']} credits, {seconds:.2f}s) as {dest.relative_to(AUTOMATION)}")


def cmd_fetch(spec_path, n, url, args):
    flow, gen = opt(args, "--flow"), opt(args, "--gen")
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    x = lines(spec)[int(n)]
    if pathlib.Path(x["file"]).exists():
        print(f"line {n} is already in the cache; nothing to fetch")
        return
    usage = load_usage()
    _log(usage, x, spec, "pending", flow, gen)  # paid from here on: never voice this line again
    save_usage(usage)
    with tempfile.TemporaryDirectory() as tmp:
        dest = pathlib.Path(tmp) / "line.mp3"
        r = subprocess.run(["curl", "-sS", "-f", "-L", "--retry", "2", "--max-time", "60", "-o", str(dest), url],
                           capture_output=True, text=True)
        if r.returncode != 0 or not dest.exists() or dest.stat().st_size < 1000:
            print(f"DOWNLOAD FAILED for line {n}: {r.stderr.strip()[-300:]}")
            print("The line is logged as paid (status pending) with its flow and generation id: a later run fetches it "
                  "with a fresh URL from creative_get_generations. Do NOT voice it again. Render this reel with Piper.")
            sys.exit(4)
        cmd_put(spec_path, n, str(dest), ["--flow", flow or "", "--gen", gen or ""])


def cmd_usage():
    usage = load_usage()
    pool = int(eleven_cfg().get("monthlyCredits", 10000))
    used = used_this_cycle(usage)
    pend = [e for e in usage["entries"] if e.get("status") == "pending"]
    print(f"cycle from {cycle_start()}: {used} of {pool} credits logged, {pool - used} left by the log "
          f"(account_get_usage has the real balance)")
    if pend:
        print(f"{len(pend)} paid line(s) still to fetch: " + ", ".join(f"{e['key']} (gen {e.get('gen')})" for e in pend))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["preflight"]:
        cmd_preflight()
    elif a[:1] == ["plan"] and len(a) >= 2:
        cmd_plan(a[1], a[2:])
    elif a[:1] == ["put"] and len(a) >= 4:
        cmd_put(a[1], a[2], a[3], a[4:])
    elif a[:1] == ["fetch"] and len(a) >= 4:
        cmd_fetch(a[1], a[2], a[3], a[4:])
    elif a[:1] == ["usage"]:
        cmd_usage()
    else:
        raise SystemExit(__doc__)
