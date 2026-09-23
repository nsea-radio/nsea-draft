# Roster &amp; net log pipeline

`roster.html` renders two kinds of data with two different owners:

```
Members edit on GitHub ──▶  data/roster.csv  ─────────────────────▶  roster.html
Google Sheet ──CSV export──▶ tools/net_log.csv ──build.py──▶ data/*.json ──▶ roster.html
```

- **`data/roster.csv`** — the public roster, committed, edited directly in the
  GitHub web editor by members. See `EDITING.md` at the repo root. The page
  parses it in the browser; no build step.
- **`tools/net_log.csv`** — the net log, still exported from the Google Sheet
  and never committed. `build.py` turns it into `data/nets.json` +
  `data/attendance.json`.

## Why the source sheet had to change shape

The current `NSEA Sunday Night Weekly Radio Net - MASTER` sheet uses **one tab per
week** (`091326 Net Log`, `090626 Net Log`, …), and each weekly tab is a **full copy
of the roster** with a `Y/N` column filled in. That one decision causes the rest:

| Symptom | Cause |
|---|---|
| "How many nets has 551 made this year?" means opening 52 tabs | attendance lives across tabs, not rows |
| A new member is absent from every past tab; a rename is inconsistent forever | roster duplicated ~52×/year |
| Tab count grows without bound | one tab per net |
| The date exists only in the tab name, as `MMDDYY` | no date column |
| No clean export range | section headers, instructions, and standing-traffic announcements sit between data rows |
| Radio type and net role can't be read separately | column E holds both (`B`, `P`, and also `Net Control-B`) |

The Master List tab is protected, which is the right instinct — but it is named
`053126` (2026-05-31), roughly three and a half months behind the weekly logs.

## The two source files

**Unit ID is the join key, not call sign.** NSEA is unit-first on the air, and call
signs are not unique here: units 521 and 524 (Brian and Charlie Drake) share
`WQPL694` on one family license.

### `data/roster.csv` — one row per unit, forever

```
unit,licensee,callsign,location,tier,show
```

- `tier` — `regular` / `authorized` / `affiliate`, replacing the section-header rows
- `show` — `no` (also `n`/`false`/`hidden`/`0`) hides the row from everything
  published: roster table, attendance rollup, and net-control/scribe name
  joins. Anything else, including blank, shows it — a forgotten cell never
  silently hides a member. Hidden check-ins still count toward per-net totals.
- Everything in this file is public by definition — `show,no` hides a row from
  the *page*, not from the repo. A member who wants no public record has no
  row; there is no notes column. Keep private information out of it.

### `tools/net_log.csv` — one row per check-in, forever

```
net_date,unit,checkin,radio_type,role,traffic,visitor_callsign,visitor_name,visitor_location
```

- `net_date` is a real ISO date (`2026-09-13`)
- `checkin` — `Y` or `L` (late)
- **A unit that did not check in gets no row.** This is the change that stops every
  net from re-copying the roster.
- `radio_type` (`M`/`P`/`B`/`CS`) and `role` (`net_control`/`scribe`) are separate
- visitors have no unit yet, so they carry their own call sign, name, and location

## Build

```sh
python3 tools/build.py
```

Reads `data/roster.csv` (for names) + `tools/net_log.csv`; writes
`data/nets.json` and `data/attendance.json`.

The build **fails** on a duplicate unit in the roster:

```
ERROR: data/roster.csv: duplicate unit 501
```

A net-log unit missing from the public roster is only a note, not an error —
that's how opted-out members' check-ins still count toward totals without
being listed by name.

`attendance.json` is the payoff — per-unit net counts in a single pass, the query
the old tab-per-week layout made impossible.

## Privacy model

`tools/*.csv` is **gitignored on purpose** — the net-log export can reference
members who opted out of the public roster. This repo is public, so anything
committed is world-readable no matter what the page chooses to render.

The rule is now structural instead of a build-time filter: **`data/roster.csv`
contains only what may be published.** Opt-out = no row. Private notes about
members do not belong anywhere in this repo.

## Updating after a net

1. In the sheet, append the night's check-ins to the flat log tab.
2. That's it — `.github/workflows/sync-netlog.yml` fetches the sheet's
   published CSV every Monday morning (or on manual dispatch), runs this
   build, and commits `data/nets.json` + `data/attendance.json` only when the
   build validates. A bad row fails the run and the site keeps the last good
   log. The workflow then chains the FTP deploy so nsea.com/nextgen updates
   too.

One-time setup: publish the flat log tab (File ▸ Share ▸ Publish to web ▸
CSV — no OAuth or service account needed) and put its URL in the repo
variable `NET_LOG_CSV_URL`. Until that variable exists the workflow skips
cleanly.

Manual fallback (works anytime): download the tab as CSV into
`tools/net_log.csv`, run `python3 tools/build.py`, commit the two JSONs.

## Outstanding

- **`data/` is currently seeded from OCR of screenshots, not a real export.** Names
  flagged in the `notes` column are unverified. Replace with a real CSV download
  before this goes to production.
- Only one net (2026-09-13) is logged, so "average check-ins" equals that one net.
- Standing traffic (next meeting date and location) should live on the website, not
  in a log sheet.
- The first-time check-in address still reads `info@nsea.com` in the sheet, the Net
  Preamble doc, and the Net Schedule doc. All three are org-owned and need updating
  to `membership@nsea.com`.
