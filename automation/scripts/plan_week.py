"""Work out the coming week's four posts from rotation.json, and record them once scheduled.

    python3 plan_week.py plan --run-date YYYY-MM-DD      # (old weekly mode) the coming week's four items
    python3 plan_week.py plan-day --run-date YYYY-MM-DD  # (current daily mode) today's one reel; exit 3 = skip
    python3 plan_week.py record --plan plan.json --results results.json
        results.json: [{"slot": 0, "date": "...", "metricoolUuid": "...", "folder": "...", "title": "..."}, ...]
        Moves 'next' on by the slots recorded (wrapping into the next cycle) and appends to history.

A weekly plan is skipped (exit code 3) when rotation.json already has history for that week's Monday.
A daily plan runs every day (config.json "daily") and is skipped only when the daily run has already
recorded today's reel (a history entry for today with "run": "daily"). Posts left from the old weekly run
don't block a day: Abr wants a reel every day even when another post is scheduled for it.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import AUTOMATION, CONFIG, GAMES  # noqa: E402

ROT = AUTOMATION / "rotation.json"
GENERAL = json.loads((AUTOMATION / "games.json").read_text(encoding="utf-8"))["general"]


def load():
    return json.loads(ROT.read_text(encoding="utf-8"))


def slot_topic(rot, cycle, index):
    """Topic for slot `index` (0-15) of cycle `cycle`."""
    kinds = rot["slots"]
    if kinds[index] == "game":
        k = sum(1 for j in range(index) if kinds[j] == "game")
        gid = rot["gameOrder"][(k + 3 * cycle) % len(rot["gameOrder"])]
        fmts = GAMES[gid]["formats"]
        return {"topic": gid, "format": fmts[cycle % len(fmts)]}
    g = sum(1 for j in range(index) if kinds[j] == "general")
    name = rot["generalOrder"][(g + cycle) % len(rot["generalOrder"])]
    return {"topic": f"general:{name}", "format": name, "brief": GENERAL[name]}


def plan(run_date):
    rot = load()
    y, m, d = map(int, run_date.split("-"))
    sunday = dt.date(y, m, d)
    if sunday.weekday() != 6:
        print(f"note: {run_date} is not a Sunday; planning the week after it anyway", file=sys.stderr)
    monday = sunday + dt.timedelta(days=(7 - sunday.weekday()) % 7 or 7)
    if any(h.get("date") == monday.isoformat() for h in rot["history"]):
        print(json.dumps({"skip": f"week of {monday} is already scheduled"}))
        sys.exit(3)
    items = []
    cycle, nxt = rot["cycle"], rot["next"]
    for i, slot in enumerate(CONFIG["week"]["slots"]):
        day = monday + dt.timedelta(days=slot["offsetDays"] - 1)
        index = (nxt + i) % 16
        c = cycle + (nxt + i) // 16
        t = slot_topic(rot, c, index)
        items.append({"slot": i, "rotationIndex": index, "cycle": c, "date": day.isoformat(), "weekday": slot["weekday"],
                      "time": slot["time"], "kind": slot["kind"], **t,
                      "folder": f"{day.isoformat()}-{t['topic'].replace('general:', '')}-{slot['kind']}"})
    month_counts = {}
    for h in rot["history"]:
        month_counts[h["date"][:7]] = month_counts.get(h["date"][:7], 0) + 1
    for it in items:
        month_counts[it["date"][:7]] = month_counts.get(it["date"][:7], 0) + 1
    over = {k: v for k, v in month_counts.items() if v > CONFIG["metricool"]["monthlyPostLimit"]}
    out = {"runDate": run_date, "monday": monday.isoformat(), "items": items, "monthCounts": month_counts,
           "overLimit": over, "note": "If overLimit is not empty, drop general slots (Saturday first) until each month is within the limit."}
    print(json.dumps(out, ensure_ascii=False, indent=1))


def plan_day(run_date):
    """Plan the single reel that the morning run makes for `run_date` (today) and posts at 9 pm the same day."""
    rot = load()
    y, m, d = map(int, run_date.split("-"))
    day = dt.date(y, m, d)
    daily = CONFIG["daily"]
    wd = day.strftime("%A")
    if wd not in daily["weekdays"]:
        print(json.dumps({"skip": f"{run_date} is a {wd}; reels go out on {', '.join(daily['weekdays'])} only"}))
        sys.exit(3)
    if any(h.get("date") == day.isoformat() and h.get("run") == "daily" for h in rot["history"]):
        print(json.dumps({"skip": f"today's reel for {run_date} is already made and recorded in rotation.json"}))
        sys.exit(3)
    index = rot["next"] % 16
    cycle = rot["cycle"] + rot["next"] // 16
    t = slot_topic(rot, cycle, index)
    item = {"slot": 0, "rotationIndex": index, "cycle": cycle, "date": day.isoformat(), "weekday": wd,
            "time": daily["time"], "kind": "reel", "run": "daily", **t,
            "folder": f"{day.isoformat()}-{t['topic'].replace('general:', '')}-reel"}
    month_counts = {}
    for h in rot["history"]:
        month_counts[h["date"][:7]] = month_counts.get(h["date"][:7], 0) + 1
    month_counts[item["date"][:7]] = month_counts.get(item["date"][:7], 0) + 1
    over = {k: v for k, v in month_counts.items() if v > CONFIG["metricool"]["monthlyPostLimit"]}
    print(json.dumps({"runDate": run_date, "items": [item], "monthCounts": month_counts, "overLimit": over,
                      "note": "One reel, posted at 9 pm today. If overLimit is not empty, stop and report it; do not schedule."},
                     ensure_ascii=False, indent=1))


def record(plan_path, results_path):
    rot = load()
    p = json.loads(pathlib.Path(plan_path).read_text(encoding="utf-8"))
    res = json.loads(pathlib.Path(results_path).read_text(encoding="utf-8"))
    by_slot = {r["slot"]: r for r in res}
    for it in p["items"]:
        r = by_slot.get(it["slot"])
        entry = {"date": it["date"], "kind": it["kind"], "topic": it["topic"], "format": it["format"],
                 "rotationIndex": it["rotationIndex"], "cycle": it["cycle"]}
        if it.get("run"):
            entry["run"] = it["run"]
        if r:
            entry.update({k: v for k, v in r.items() if k != "slot"})
        else:
            entry["note"] = "skipped"
        rot["history"].append(entry)
    advanced = len(p["items"])
    total = rot["next"] + advanced
    rot["cycle"] += total // 16
    rot["next"] = total % 16
    ROT.write_text(json.dumps(rot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"recorded {len(res)} posts; next slot {rot['next']} of cycle {rot['cycle']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("plan")
    a.add_argument("--run-date", required=True)
    c = sub.add_parser("plan-day")
    c.add_argument("--run-date", required=True)
    b = sub.add_parser("record")
    b.add_argument("--plan", required=True)
    b.add_argument("--results", required=True)
    args = ap.parse_args()
    if args.cmd == "plan":
        plan(args.run_date)
    elif args.cmd == "plan-day":
        plan_day(args.run_date)
    else:
        record(args.plan, args.results)
