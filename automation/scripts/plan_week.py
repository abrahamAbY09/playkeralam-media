"""Plan Play Keralam's Instagram reels from rotation.json, and record them once scheduled.

    python3 plan_week.py plan --run-date YYYY-MM-DD      # (old weekly mode) the coming week's four items
    python3 plan_week.py plan-day --run-date YYYY-MM-DD  # (current daily mode) today's one reel; exit 3 = skip
    python3 plan_week.py calendar --month YYYY-MM [--start YYYY-MM-DD]  # posting days for a month, by Abr's rule
    python3 plan_week.py record --plan plan.json --results results.json
        results.json: [{"slot": 0, "date": "...", "metricoolUuid": "...", "folder": "...", "title": "..."}, ...]
        Moves 'next' on by the slots recorded (wrapping into the next cycle) and appends to history.

The daily run fires every morning, but posts only on the dates in config.json "daily" -> "postDates"
(one list per month). Abr's rule (23 Oct 2026), made to fit Metricool's free plan of 20 published posts a
month: post on every Tuesday, Thursday, Saturday and Sunday, then spread whatever the cap leaves evenly over
Mondays, Wednesdays and Fridays through the month. `calendar` works that out for a month; paste its dates
into postDates. A month with no list gets no reels (the run stops and says the calendar needs extending).

A daily plan is also skipped when the daily run has already recorded today's reel (a history entry for
today with "run": "daily"). Posts left from the old weekly run don't block a posting day.
"""
import argparse
import calendar
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
    month = day.isoformat()[:7]
    dates = daily["postDates"].get(month)
    if dates is None:
        print(json.dumps({"skip": f"no posting calendar for {month} yet: extend config.json daily.postDates "
                                  f"(python3 automation/scripts/plan_week.py calendar --month {month})"}))
        sys.exit(3)
    if day.isoformat() not in dates:
        print(json.dumps({"skip": f"{run_date} ({wd}) is not a posting day in the {month} calendar"}))
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


MUST_DAYS = ("Tuesday", "Thursday", "Saturday", "Sunday")
SPREAD_DAYS = ("Monday", "Wednesday", "Friday")


def month_calendar(month, start=None):
    """Posting days for `month` (YYYY-MM) by Abr's rule: every Tuesday, Thursday, Saturday and Sunday, then
    the posts the monthly cap leaves spread evenly over Mondays, Wednesdays and Fridays across the month.
    With `start` (YYYY-MM-DD) only days from `start` on are planned, and posts already in rotation.json for
    that month (earlier days, or old weekly-run posts) count against the cap."""
    rot = load()
    y, m = map(int, month.split("-"))
    first = dt.date(y, m, 1)
    begin = dt.date.fromisoformat(start) if start else first
    days = [first + dt.timedelta(i) for i in range(calendar.monthrange(y, m)[1])]
    days = [d for d in days if d >= begin]
    planned = {d.isoformat() for d in days}
    existing = [h for h in rot["history"] if h["date"][:7] == month
                and not (h["date"] in planned and h.get("run") == "daily")]
    must = [d for d in days if d.strftime("%A") in MUST_DAYS]
    cands = [d for d in days if d.strftime("%A") in SPREAD_DAYS]
    room = CONFIG["metricool"]["monthlyPostLimit"] - len(existing) - len(must)
    if room >= len(cands):
        extras = cands
    else:
        extras, used = [], {}
        span = days[-1].day - days[0].day + 1
        for i in range(max(room, 0)):
            target = days[0].day - 0.5 + (i + 0.5) * span / room
            pick = min((d for d in cands if d not in extras),
                       key=lambda d: (used.get(d.strftime("%A"), 0), abs(d.day - target), d.day))
            extras.append(pick)
            used[pick.strftime("%A")] = used.get(pick.strftime("%A"), 0) + 1
    dates = sorted(d.isoformat() for d in must + extras)
    return {"month": month, "dates": dates, "spreadDays": sorted(d.isoformat() for d in extras),
            "alreadyInMonth": len(existing), "total": len(existing) + len(dates),
            "limit": CONFIG["metricool"]["monthlyPostLimit"]}


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
    k = sub.add_parser("calendar")
    k.add_argument("--month", required=True)
    k.add_argument("--start")
    b = sub.add_parser("record")
    b.add_argument("--plan", required=True)
    b.add_argument("--results", required=True)
    args = ap.parse_args()
    if args.cmd == "plan":
        plan(args.run_date)
    elif args.cmd == "plan-day":
        plan_day(args.run_date)
    elif args.cmd == "calendar":
        print(json.dumps(month_calendar(args.month, args.start), indent=1))
    else:
        record(args.plan, args.results)
