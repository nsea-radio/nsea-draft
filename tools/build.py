#!/usr/bin/env python3
"""
Build published net-log JSON for the NSEA site.

    data/roster.csv    (committed, member-edited)  -> names/units for joins
    tools/net_log.csv  (sheet export, NOT committed) -> data/nets.json
                                                     -> data/attendance.json

Usage, from the repo root:

    python3 tools/build.py

The roster itself is no longer built here: data/roster.csv is the committed
source of truth, edited directly on GitHub by members (see EDITING.md), and
roster.html renders it as-is. Everything in that file is public by
definition -- a member who does not want to be listed simply has no row, and
there is no notes column. Keep private information out of it.

tools/net_log.csv is still the Google Sheet export and stays uncommitted
(see .gitignore): it can reference units that opted out of the public roster.
Those check-ins still count toward per-net totals, but only units present in
data/roster.csv get a named attendance row.
"""

import csv
import json
import pathlib
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "tools"
OUT = ROOT / "data"

# Column E in the legacy sheet mixed equipment type with net role. We split
# them, and these are the only equipment values the preamble actually names.
RADIO_TYPES = {
    "M": "Mobile",
    "P": "Portable",
    "B": "Base",
    "CS": "Control Station",
}
# Y = checked in, L = late check-in. A unit with no row simply did not check in;
# the legacy sheet wrote an explicit N on every roster row every week, which is
# what made each weekly tab a full roster copy.
CHECKED_IN = {"Y", "L"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [
            {k: (v or "").strip() for k, v in row.items() if k}
            for row in csv.DictReader(fh)
        ]


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# Values of the `show` column that hide a row from everything published
# (roster table, attendance rollup, net-control/scribe name joins). Anything
# else -- including a blank cell -- keeps the row visible, so a forgotten
# value never silently hides a member.
HIDDEN = {"no", "n", "false", "hidden", "0"}


def load_roster(rows):
    """data/roster.csv sanity check. Returns (shown_records, unit_index)."""
    index, seen, problems = {}, set(), []

    shown = [r for r in rows if r.get("show", "").lower() not in HIDDEN]

    for row in shown:
        unit = row["unit"]
        if not unit:
            problems.append("row with empty unit")
            continue
        if unit in seen:
            problems.append(f"duplicate unit {unit}")
        seen.add(unit)
        index[unit] = row

    if problems:
        fail("data/roster.csv: " + "; ".join(problems))

    return shown, index


def build_nets(rows, roster_index):
    """Per-net summaries, newest first."""
    nets = defaultdict(list)
    for row in rows:
        if not row["net_date"]:
            fail("net_log.csv: row with empty net_date")
        nets[row["net_date"]].append(row)

    # Units missing from the public roster are fine (opted out / not yet
    # added): their check-ins count, they just render without a name.
    unknown = {
        r["unit"]
        for rs in nets.values()
        for r in rs
        if r["unit"] and r["unit"] not in roster_index
    }
    if unknown:
        print(f"note: units not in data/roster.csv: {sorted(unknown)}")

    out = []
    for date in sorted(nets, reverse=True):
        entries = nets[date]
        checked = [r for r in entries if r["checkin"] in CHECKED_IN]

        def who(role):
            hit = next((r for r in entries if r["role"] == role), None)
            if not hit:
                return None
            member = roster_index.get(hit["unit"], {})
            return {
                "unit": hit["unit"],
                "licensee": member.get("licensee", ""),
                "callsign": member.get("callsign", "").upper(),
            }

        visitors = [
            {
                "callsign": r["visitor_callsign"].upper(),
                "name": r["visitor_name"],
                "location": r["visitor_location"],
            }
            for r in entries
            if r["visitor_callsign"]
        ]

        out.append(
            {
                "date": date,
                "check_ins": len(checked),
                "late": sum(1 for r in checked if r["checkin"] == "L"),
                "traffic": sum(1 for r in checked if r["traffic"] == "Y"),
                "net_control": who("net_control"),
                "scribe": who("scribe"),
                "visitors": visitors,
                "radio_types": {
                    RADIO_TYPES[k]: v
                    for k, v in sorted(
                        Counter(
                            r["radio_type"] for r in checked if r["radio_type"]
                        ).items()
                    )
                    if k in RADIO_TYPES
                },
            }
        )
    return out


def build_attendance(rows, roster_index, published):
    """Per-unit attendance rollup -- the query the old format made impossible."""
    total_nets = len({r["net_date"] for r in rows})
    counts = Counter(
        r["unit"] for r in rows if r["unit"] and r["checkin"] in CHECKED_IN
    )
    public_units = {r["unit"] for r in published}

    records = [
        {
            "unit": unit,
            "licensee": roster_index[unit]["licensee"],
            "callsign": roster_index[unit]["callsign"].upper(),
            "nets_attended": counts.get(unit, 0),
            "pct": round(100 * counts.get(unit, 0) / total_nets) if total_nets else 0,
        }
        for unit in public_units
    ]
    records.sort(key=lambda r: (-r["nets_attended"], r["unit"]))
    return {"total_nets": total_nets, "units": records}


def main():
    roster_rows = read_csv(OUT / "roster.csv")
    log_rows = read_csv(SRC / "net_log.csv")

    published, index = load_roster(roster_rows)
    nets = build_nets(log_rows, index)
    attendance = build_attendance(log_rows, index, published)

    OUT.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "nets.json": {"count": len(nets), "nets": nets},
        "attendance.json": attendance,
    }
    for name, payload in artifacts.items():
        (OUT / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"nets.json       {len(nets)} nets")
    print(f"attendance.json {attendance['total_nets']} nets rolled up")


if __name__ == "__main__":
    main()
