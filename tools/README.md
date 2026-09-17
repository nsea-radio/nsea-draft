# Roster &amp; net log pipeline

`roster.html` renders from three generated JSON files in `data/`. Those are built
from two CSVs by `tools/build.py`. The CSVs come out of the Google Sheet.

```
Google Sheet  ──File ▸ Download ▸ CSV──▶  tools/*.csv  ──build.py──▶  data/*.json  ──▶  roster.html
```

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

### `tools/roster.csv` — one row per unit, forever

```
unit,licensee,callsign,location,tier,status,publish_public,notes
```

- `tier` — `regular` / `authorized` / `affiliate`, replacing the section-header rows
- `status` — `active` / `inactive` / `deceased`
- `publish_public` — per-member opt-in; withheld rows never reach `data/`
- `notes` — private, never published

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

Writes `data/roster.json`, `data/nets.json`, `data/attendance.json`.

The build **fails** on a duplicate unit, or on a net-log row citing a unit that
isn't in the roster:

```
ERROR: roster.csv: duplicate unit 501
ERROR: net_log.csv references units absent from roster.csv: ['999']
```

That is the typo protection the spreadsheet has never had.

`attendance.json` is the payoff — per-unit net counts in a single pass, the query
the old tab-per-week layout made impossible.

## Privacy model

`tools/*.csv` is **gitignored on purpose.** The CSVs hold the private `notes`
column and the rows of members who opted out; this repo is public, so anything
committed under `data/` is world-readable no matter what the page chooses to
render. Redaction happens in `build.py`, before anything is written.

Keep the CSVs locally, or in a private repo. The sheet remains the source of truth.

## Updating after a net

1. In the sheet, append the night's check-ins to the flat log tab
2. File ▸ Download ▸ Comma-separated values, into `tools/net_log.csv`
3. `python3 tools/build.py`
4. Commit `data/*.json`

Once the tabs are published to the web (File ▸ Share ▸ Publish to web ▸ CSV),
steps 2–4 can run unattended in a GitHub Action — the published-CSV endpoint needs
no OAuth, no service account, and no API enablement.

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
