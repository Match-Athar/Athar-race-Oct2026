# Athar (أثر) dashboards

The daily build for IBRAQ's monthly branch-incentive program. Each day it turns two Excel files into two web pages:

| Page | File | Audience | Contains |
|---|---|---|---|
| **«سباق أثر»** (public board) | `site/index.html` | Branch staff, shared by link | Percentages, ranks and employee names. **No amounts.** |
| **«لوحة أثر»** (internal board) | `site/internal.html` | Sales management only | Sales and targets in local currency and SAR, the full ranking, review flags and top employees. |

Both pages are single self-contained HTML files. Each one opens on any phone or computer and works on any static host, with no server or login.

- **Inputs:** the daily Odoo POS export and the monthly target file (details in [docs/RULES.md](docs/RULES.md)).
- **Rules:** all prize rules, FX rates and decisions are in [docs/RULES.md](docs/RULES.md).

---

## 1. Folder map

```
run.py                   one command that builds everything
athar/config.py          FX rates, quotas, prizes, exclusions       ← change numbers here
athar/rules.py           prize allocation (single source of truth)  ← change rules here
athar/readers.py         reads the Odoo export (both layouts) + target file
athar/build.py           builds the JSON for each page (public build refuses any amount)
athar/render.py          injects the JSON into a template → full web page
athar/export.py          CSV tables for a database (Supabase)
templates/public.html    design of «سباق أثر» (data-free template)
templates/internal.html  design of «لوحة أثر» (data-free template)
tests/test_rules.py      rule tests (car, small markets, moved seats, dropped prizes)
tests/check_ts_port.py   proves lovable/athar-rules.ts gives the same prizes as Python
supabase/schema.sql      tables + public views for a live database version
lovable/athar-rules.ts   the rules in TypeScript, for a Lovable/React app
lovable/PROMPT.md        step-by-step + prompt to rebuild as a live app
.github/workflows/publish.yml   auto-publish the public board on GitHub Pages
data/                    put the Excel files here (pos.xlsx, target.xlsx)
site/                    output
```

## 2. Run it on your computer (5 minutes, once)

1. Install Python 3.10 or newer from python.org.
2. Open a terminal in this folder and run `pip install -r requirements.txt`.
3. Copy the files into `data/`:
   - the month's target file as `data/target.xlsx`
   - today's Odoo export as `data/pos.xlsx`
4. Run:

   ```
   python run.py --pos data/pos.xlsx --target data/target.xlsx
   ```

   It prints a summary like this:

   ```
   Data through 2026-10-13: 23.25M SAR, achievement 37.0% vs expected 41.9%, on track 59
   Car leader (projected): ZAHIA | seats filled {...} | moved to KSA [...]
   ```

5. Open `site/index.html` (public) and `site/internal.html` (internal) in a browser.

**Odoo export tip:** export the pivot with **days as columns**. The date is then read automatically, and the boards get "today's change", rank arrows, best day and the trend. With the older single-total export, add `--asof 2026-10-13`. That layout works, but without the daily features.

**Sales straight from the Odoo BI API (no export):** targets still come from `data/target.xlsx`. Put the endpoint and token in `.env` (a copy of `.env.example`):

```
ODOO_API_URL=https://<odoo-host>/api/bi/v1/pos/sales/detail
ODOO_API_TOKEN=<bearer token>
```

then use `--api` in place of `--pos`:

```
python run.py --api --target data/target.xlsx
```

`.env` is listed in `.gitignore`, so it is never uploaded. Environment variables with the same names override it (that is how a server or GitHub Actions secret would supply them).

How it reads the API:

- **Dates:** the API works in **UTC** (`date_from`, `date_to`, `date_order`); the dashboard works in **GCC time** (`ODOO_TZ`, default `Asia/Riyadh` = UTC+3). Each GCC day is asked as `D-1 21:00:00 .. D 20:59:59` UTC, from the 1st of the month to today (or `--asof YYYY-MM-DD`).
- **Paging:** 2,000 orders per page (`limit`/`offset`), until `meta.has_more` is false.
- **Amounts:** `amount_wod_excl_tax` is the sales amount (own currency, refunds negative). Orders are summed per day, `store_name` and `cashier_name` (the POS user); `amount_wod_incl_tax` is summed the same way and kept as `sales_incl` in the internal data.
- **Cache:** a month is hundreds of thousands of orders, so each finished day is downloaded once and kept in `data/api_cache/` (one small file per day, per branch and cashier). Every run only downloads **today and yesterday** again. Delete a day's file to force it to be downloaded again (e.g. after back-dated corrections in Odoo).
- `store_name` must match the Store column of the target file (upper/lower case does not matter). Unmatched branches are printed as a warning.
- **Today while it is still running:** live data includes today's sales so far. They count towards each branch's achievement, but the pace, projections and prize seats divide by the **finished** days only (e.g. 17 on 18 Oct), so a half-done day never pulls every projection down and removes seats in the morning. The pages still show the calendar day ("18 / 31", 14 days left including today). Excel files, and API runs that end on a finished day, work exactly as before. (On the 1st of the month the first day counts as 1, since there is no finished day yet.)
- **Testing with a fixed date range:** set `SALES_DATE_FROM` / `SALES_DATE_TO` (GCC dates, `YYYY-MM-DD`) in `.env`, e.g. `2026-08-01` and `2026-08-05` when the test API has no data for the current month. Each run then prints `TEST date range from .env: …`. Only FROM = from that day to today; only TO = from the 1st of that month to that day. The "expected" pace is still worked out from where the TO date falls in its month, and achievement is against the monthly target. **Empty both for the live dashboard.**

The code is in `athar/api.py`.

**Everyday use:** double-click **`start_live.bat`**. One window does both: it pulls the API right away and then every 5 minutes, and shows the boards at `http://localhost:8000/internal.html` and `http://localhost:8000/` with the **Refresh now** button below. Run only one start file at a time (both use port 8000).

**"Refresh now" button only (no automatic refresh):** double-click **`start_dashboard.bat`** (or run `python run.py --api --target data/target.xlsx --serve`). It opens the boards at `http://localhost:8000/` (public) and `http://localhost:8000/internal.html` (internal), with a **🔄 تحديث الآن** button in the header. A click pulls the latest sales from the API (today and yesterday; earlier days come from the cache, so it takes seconds), rebuilds both boards and reloads the page. A second click while one is running is refused. The button exists only when the pages are opened through this local server: the files in `site/` and anything published to github.io are unchanged and have no button. There is no automatic refresh in this mode unless you add `--every` (e.g. `--serve --every`). It only listens on this computer; `--host 0.0.0.0` would let other PCs on the network open it (the internal board has all amounts).

**Keep it up to date automatically (every 5 minutes):** double-click **`start_live.bat`** and leave the window open, or run:

```
python run.py --api --target data/target.xlsx --every
```

`--every` on its own means 5 minutes (`REFRESH_MINUTES` in `run.py`); `--every 10` picks another interval (1 minute at least).

- It rebuilds `site/` every 5 minutes, always up to today (it moves to the new day and month by itself; `--asof` is not allowed here). The target file is re-read each round, so replacing it for a new month needs no restart.
- The pages it writes reload themselves on the same interval, so an open board shows the new numbers without anyone pressing refresh. The internal page does not reload while its upload panel is open or after someone uploaded a file there.
- If the API is down, that round is skipped and the previous pages stay; it tries again next round. Stop it with Ctrl+C.
- This updates the files on **this computer**. People only see the new numbers if they open the pages from here (or from a shared folder/web server pointing at `site/`). A board uploaded to GitHub Pages or Netlify only changes when it is re-uploaded.

**Database tables:** add `--csv` to also write the tables for a database into `site/csv/`.

## 3. Daily routine: pick one

### A. Automatic link with GitHub (recommended for sharing)

Setup, once:

1. Create a **private** repository on github.com and upload this whole folder.
2. In the repository, go to **Settings → Pages → Source** and choose **GitHub Actions**.
3. Upload `data/target.xlsx` once a month.

Every day:

1. In the repository, open the `data/` folder and choose **Add file → Upload files**.
2. Upload the Odoo export renamed to **`pos.xlsx`** (it replaces yesterday's).
3. Commit.

About a minute later the public board is live at `https://<your-account>.github.io/<repo>/`. Send that link to the branches once; it updates itself every day.

- **Repository must be private.** The workflow publishes **only** the public board, and the Excel files in the repo contain amounts.
- **Private repos and Pages:** publishing Pages from a private repository needs a paid GitHub plan (Pro, Team or Enterprise). With a free plan, use option B for hosting.
- **The page is public.** The published page is open to anyone who has the link. It contains employee names, so confirm consent first (guide §11).

### A2. GitHub without git (what we set up for IBRAQ)

The repo holds **only** the public `index.html`, so it can be a free **public** repository.

- **Code and Excel files:** these stay in your OneDrive folder.
- **One-time:** create a GitHub account, then create a token (classic, scope `public_repo`) and save it as `github-token.txt` in this folder. Don't paste the token in any chat.
- **Every day:**

  ```
  python run.py --pos data/pos.xlsx --target data/target.xlsx --public-only
  python publish_github.py --token-file github-token.txt --page site/index.html
  ```

  The first run creates the `athar-race` repository and turns on Pages. The link is `https://<user>.github.io/athar-race/`.

### B. Any static host (Netlify, Cloudflare Pages, company website)

Run step 2 on your computer, then upload `site/index.html` to the host and replace it daily.

- **Netlify:** drag the `site` folder (after deleting `internal.html`, `data/` and `csv/`) onto app.netlify.com/drop.
- **Your IT team** can put `index.html` on the company website instead.
- **Never upload `internal.html` to an open link**, because it has every amount. Keep it on your computer, share it by email, or put it behind a login.

### C. Live app with database (Supabase + Lovable)

Admins upload the Odoo file in the app and everyone sees the update immediately, with a proper login for the internal side. Follow [lovable/PROMPT.md](lovable/PROMPT.md). The database views are already written and were tested against real data.

## 4. Changing things safely

| I want to… | Edit | Then |
|---|---|---|
| Change an FX rate, quota, prize name or the car threshold | `athar/config.py`, plus the same constants near the top of the script in `templates/internal.html` (the internal page recalculates when you upload in the browser) and in `lovable/athar-rules.ts` if you use it | `python tests/test_rules.py` |
| Change how prizes are allocated | `athar/rules.py` and `lovable/athar-rules.ts` | both test commands below |
| Change wording or design | `templates/public.html` / `templates/internal.html`. The JSON fields each page reads are listed in `athar/build.py`. | rebuild and open in a browser |
| New month | Replace `data/target.xlsx` | — |

Tests:

```
python tests/test_rules.py
python tests/check_ts_port.py data/pos.xlsx data/target.xlsx   # needs Node.js, only if you use the TS port
```

## 5. Data notes

**Public board fields** (`site/data/public.json`, per branch, no amounts):

| Field | Meaning |
|---|---|
| `s` | Code |
| `c` | Country |
| `city` | City |
| `a` | Achievement |
| `d` | Change today |
| `p` | Projected |
| `r` / `rp` | Rank today / yesterday |
| `aw` | Projected prize (A–E) |
| `mv` | Moved seat |
| `top` | Top 3 employees, e.g. `SHussein (1900)` |
| `bd` / `bdd` | Best day (as points of target) and which day |

**Internal board:**
- The page recalculates everything in the browser from the embedded month-to-date data, so it can also take a new Odoo file through its **تحديث البيانات** button. Outside Claude, an upload updates only that viewer's screen; to update everyone, rebuild and re-upload the page.
- The month trend is drawn from the day columns embedded in the page.

## 6. Verified

- **Rebuilt from the 13 Oct 2026 file:**
  - prizes, seats, moved seats, percentages and ranks match the live boards for all 226 branches;
  - the TypeScript rules match Python;
  - the Supabase views match Python for all 226 branches;
  - both pages open with no errors as plain web pages, on desktop and phone widths.
- **Fixed during extraction:** the earlier build read the public board's top-3 employee names from an old 10 Oct snapshot. This version always reads them from the file being processed.
