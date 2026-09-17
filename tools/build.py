#!/usr/bin/env python3
"""
Build published JSON for the NSEA site from the two source CSVs.

    tools/roster.csv   -> data/roster.json     (public fields only)
    tools/net_log.csv  -> data/nets.json       (per-net summaries)
                       -> data/attendance.json (per-unit rollup)

Usage, from the repo root:

    python3 tools/build.py

Source CSVs are exports of the Google Sheet tabs and are deliberately NOT
committed (see .gitignore) -- they carry the private notes column and the rows
of members who opted out of public listing. Export them from the sheet with
File > Download > Comma-separated values, then run this.

PRIVACY: only roster rows with publish_public=yes AND status=active reach
roster.json, and the notes column is never published. Filtering happens here,
before anything is written -- not in the browser, because this repo is public
and every file in data/ is world-readable regardless of what the page renders.
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


def build_roster(rows):
    """Public roster. Returns (published_records, unit_index_of_all_rows)."""
    index, seen, problems = {}, set(), []

    for row in rows:
        unit = row["unit"]
        if not unit:
            problems.append("row with empty unit")
            continue
        if unit in seen:
            problems.append(f"duplicate unit {unit}")
        seen.add(unit)
        index[unit] = row

    if problems:
        fail("roster.csv: " + "; ".join(problems))

    published = [
        {
            "unit": r["unit"],
            "licensee": r["licensee"],
            "callsign": r["callsign"].upper(),
            "location": r["location"],
            "tier": r["tier"],
        }
        for r in rows
        if r["publish_public"] == "yes" and r["status"] == "active"
    ]

    def sort_key(r):
        # Numeric units first in numeric order, free-text units last.
        return (0, int(r["unit"]), "") if r["unit"].isdigit() else (1, 0, r["unit"])

    published.sort(key=sort_key)
    return published, index


def build_nets(rows, roster_index):
    """Per-net summaries, newest first."""
    nets = defaultdict(list)
    for row in rows:
        if not row["net_date"]:
            fail("net_log.csv: row with empty net_date")
        nets[row["net_date"]].append(row)

    unknown = {
        r["unit"]
        for rs in nets.values()
        for r in rs
        if r["unit"] and r["unit"] not in roster_index
    }
    if unknown:
        fail(f"net_log.csv references units absent from roster.csv: {sorted(unknown)}")

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
    roster_rows = read_csv(SRC / "roster.csv")
    log_rows = read_csv(SRC / "net_log.csv")

    published, index = build_roster(roster_rows)
    nets = build_nets(log_rows, index)
    attendance = build_attendance(log_rows, index, published)

    OUT.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "roster.json": {
            "updated": max(n["date"] for n in nets) if nets else None,
            "count": len(published),
            "members": published,
        },
        "nets.json": {"count": len(nets), "nets": nets},
        "attendance.json": attendance,
    }
    for name, payload in artifacts.items():
        (OUT / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    withheld = len(roster_rows) - len(published)
    print(f"roster.json     {len(published)} published, {withheld} withheld")
    print(f"nets.json       {len(nets)} nets")
    print(f"attendance.json {attendance['total_nets']} nets rolled up")


if __name__ == "__main__":
    main()
