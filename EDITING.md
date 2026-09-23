# Editing the NSEA roster

The member roster on the website comes from **one file in this repository**:

> [`data/roster.csv`](data/roster.csv)

Edit that file, save it, and the [roster page](https://nsea-radio.github.io/nsea-draft/roster.html)
updates itself about a minute later. You never need to touch the website's HTML.

## How to make an edit

1. **Sign in** to [github.com](https://github.com) (you need to be added as a
   collaborator once — ask Eric).
2. Open the file: [`data/roster.csv`](data/roster.csv).
3. Click the **pencil icon** (✏️, top-right of the file view) — "Edit this file."
4. Make your change (see the format below).
5. Click the green **Commit changes…** button. In the box that pops up, write a
   short note about what you changed, e.g. `Add unit 612 — Jane Smith`.
   Leave **"Commit directly to the main branch"** selected.
6. Wait about a minute, then refresh the
   [roster page](https://nsea-radio.github.io/nsea-draft/roster.html) to see it live.

## The format

One line per member, five values separated by commas, in this order:

```
unit,licensee,callsign,location,tier
```

For example:

```
547,Gary Edelman,WQOR681,Skokie,regular
```

- **unit** — the NSEA unit number (e.g. `547`)
- **licensee** — the member's name
- **callsign** — the GMRS call sign (e.g. `WQOR681`)
- **location** — town
- **tier** — exactly one of: `regular`, `authorized`, or `affiliate`

Rules of thumb:

- **Copy an existing line** and change the values — that's the easiest way to
  get it right.
- Don't remove the first line (`unit,licensee,callsign,location,tier`) — it's
  the header.
- If a value itself contains a comma (like `Sodus, MI`), wrap that value in
  double quotes: `"Sodus, MI"`.
- Don't worry about keeping the file sorted — the page sorts by unit number
  automatically.

## Common tasks

- **Add a member:** add a new line anywhere below the header.
- **Remove a member:** delete their whole line.
- **Fix a typo:** edit the value in place.

## Privacy — read this before adding anyone

**Everything in this file is public on the internet.** Only list members who
have agreed to appear on the public roster. If someone doesn't want to be
listed, they simply have no line here — their weekly net check-ins still count
toward the totals on the page.

Never put phone numbers, email addresses, street addresses, or private notes
in this file.

## Made a mistake?

Don't panic — every change is saved in history and nothing is ever lost.

- If the roster looks wrong, just edit the file again and fix it.
- A badly formatted line won't break the page; that line is simply skipped
  until it's fixed.
- If you're stuck, tell Eric what happened — any previous version can be
  restored in a couple of clicks (file page → **History**).
