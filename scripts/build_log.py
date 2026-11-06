"""Builds the daily markdown logs and README for sde-journey.

Input: a JSON dump with keys "plan", "progress" and "logs" exported from my
SDE-1 tracker. Usage: python scripts/build_log.py dump.json
Only numbers and topic names are published. Personal notes are never written.
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACK_NAMES = {"dsa": "DSA", "cs": "CS fundamentals", "proj": "Project", "oa": "OA and interview rounds", "lld": "Low level design", "iv": "Interview prep"}


def slug(name):
    s = str(name).lower().replace("-", " ")
    s = re.sub(r"[^a-z0-9 ]", "", s).strip()
    return re.sub(r"\s+", "-", s)


def item_index(plan):
    idx = {}
    for tr in plan.get("tracks", []):
        for tp in tr.get("topics", []):
            for name in tp.get("p", []) or []:
                idx[tr["id"] + ":" + slug(name)] = {"name": name, "topic": tp["t"], "track": tr["id"]}
    return idx


def is_date(v):
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)))


def nice(d):
    return date.fromisoformat(d).strftime("%a %d %b %Y")


def day_md(d, items, prog, log):
    done = [(i, items[i]) for i, v in prog.get("doneAt", {}).items() if v == d and i in items]
    by = {}
    for i, it in done:
        by.setdefault(it["track"], []).append((i, it))
    quiz = prog.get("quiz", {})
    out = ["# " + nice(d), ""]
    for tr in ["dsa", "cs", "proj", "oa", "lld", "iv"]:
        if tr not in by:
            continue
        out.append("## " + TRACK_NAMES[tr])
        for i, it in by[tr]:
            if tr == "dsa":
                out.append("- [{0}](https://leetcode.com/problems/{1}/) ({2})".format(it["name"], slug(it["name"]), it["topic"]))
            else:
                q = quiz.get(i)
                qs = " · quiz {0}/{1}".format(q["s"], q["n"]) if q and q.get("d") == d else ""
                out.append("- {0} ({1}){2}".format(it["name"], it["topic"], qs))
        out.append("")
    reads = [k for k, v in prog.get("read", {}).items() if v == d]
    if reads:
        out.append("## Topic notes read")
        out += ["- " + k.split(":", 1)[1].replace("-", " ").title() for k in reads]
        out.append("")
    lg = log or {}
    out.append("## Numbers")
    out.append("| Metric | Count |")
    out.append("|---|---|")
    rev = lg.get("rev", prog.get("revAt", {}).get(d, 0)) or 0
    rows = [("DSA problems solved", len(by.get("dsa", []))), ("Problems revisited", rev), ("Job applications", lg.get("apps", 0)), ("Referral messages", lg.get("dms", 0)),
            ("Bug-fix drills", (prog.get("drills", {}).get(d) or {}).get("n", lg.get("drills", 0))), ("Gym", "rest day" if lg.get("rest") else ("yes" if lg.get("gym") else "no"))]
    out += ["| {0} | {1} |".format(a, b) for a, b in rows]
    out.append("")
    return "\n".join(out)


def active_days(items, prog, logs):
    days = set(v for v in prog.get("doneAt", {}).values() if is_date(v))
    days |= set(v for v in prog.get("read", {}).values() if is_date(v))
    for d, lg in logs.items():
        if lg.get("dsa") or lg.get("cs") or lg.get("proj") or lg.get("apps") or lg.get("rev"):
            days.add(d)
    return days


def main(path):
    data = json.loads(Path(path).read_text())
    plan, prog = data["plan"], data["progress"]
    logs = {l["date"]: l for l in data.get("logs", []) if l and l.get("date")}
    items = item_index(plan)
    days = sorted(active_days(items, prog, logs))
    for d in days:
        p = ROOT / "days" / d[:7] / (d + ".md")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(day_md(d, items, prog, logs.get(d)))

    solved = int(prog.get("base", 0)) + len(prog.get("recent", []))
    done_ids = [i for i in prog.get("done", {}) if i in items]
    count = lambda tr: sum(1 for i in done_ids if items[i]["track"] == tr)
    total = lambda tr: sum(1 for i in items if items[i]["track"] == tr)
    # streak of active days ending today or yesterday
    s, d = 0, date.today()
    if d.isoformat() not in days:
        d -= timedelta(days=1)
    while d.isoformat() in days:
        s += 1
        d -= timedelta(days=1)

    recent = days[-14:][::-1]
    lines = [
        "# SDE Journey",
        "",
        "Daily public log of my preparation for an SDE-1 role: DSA, CS fundamentals, a backend project, and interview rounds.",
        "Updated automatically every night from my study tracker.",
        "",
        "## Where I am",
        "",
        "| | |",
        "|---|---|",
        "| DSA problems solved | {0} |".format(solved),
        "| CS fundamentals topics | {0} / {1} |".format(count("cs"), total("cs")),
        "| Project steps | {0} / {1} |".format(count("proj"), total("proj")),
        "| Active days in a row | {0} |".format(s),
        "| Last updated | {0} |".format(date.today().strftime("%d %b %Y")),
        "",
        "## Last 14 active days",
        "",
        "| Day | DSA | CS | Project | Applications |",
        "|---|---|---|---|---|",
    ]
    for d in recent:
        dd = [i for i, v in prog.get("doneAt", {}).items() if v == d and i in items]
        c = lambda tr: sum(1 for i in dd if items[i]["track"] == tr)
        lines.append("| [{0}](days/{1}/{2}.md) | {3} | {4} | {5} | {6} |".format(nice(d), d[:7], d, c("dsa"), c("cs"), c("proj"), (logs.get(d) or {}).get("apps", 0)))
    lines += ["", "## Folders", "", "- `days/`: one file per day", "- `dsa/`: my own solutions, pushed by hand", "- `scripts/`: the script that builds these logs", ""]
    (ROOT / "README.md").write_text("\n".join(lines))
    print("days:", len(days), "solved:", solved, "streak:", s)


if __name__ == "__main__":
    main(sys.argv[1])
