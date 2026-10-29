# Deploying the MATCH race board on GitHub Pages

The board builds itself from the **live Odoo API** plus the reference workbook and
publishes with GitHub Pages. No daily upload — once it's set up it refreshes on its own.

- Sales, transactions, staff and last-year come from the Odoo BI API (tax-included).
- Targets, the daily curve, prize ceilings, names, area managers and footfall come from
  `data/master.xlsx` (committed to the repo).
- Workflow: [`.github/workflows/publish.yml`](.github/workflows/publish.yml).

## What gets published

| Page | Published? | Contains |
|---|---|---|
| `index.html` — race board | ✅ yes | percentages, ranks, employee names |
| `public.html` — public board | ✅ yes | percentages and names, no amounts |
| `internal.html` — amounts | ❌ never | kept out of the build (`--public-only`) |

The published page is reachable by **anyone with the link**. Keep the repository
**private** (the reference workbook holds sales amounts), and confirm name-display consent.

> Publishing Pages from a **private** repo needs a paid GitHub plan (Pro / Team / Enterprise).
> On a free plan, keep the repo private and host the built `site/` folder elsewhere (e.g. Netlify).

## One-time setup

### 1. Push the project to a new private repo

```bash
git init
git add .
git commit -m "MATCH race board"
git branch -M main
git remote add origin https://github.com/<account>/<repo>.git
git push -u origin main
```

`.env` and `github-token.txt` are git-ignored, so your API token is **not** pushed.
`data/master.xlsx` **is** pushed (the build needs it) — that's why the repo must be private.

### 2. Add the API secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `ODOO_API_URL` | `https://matchperfume.odoo.com/api/bi/v1/pos/sales/detail` |
| `ODOO_API_TOKEN` | your production bearer token |
| `ODOO_TZ` | optional — `Asia/Riyadh` (default) or `Asia/Dubai` |

The full `/api/bi/v1/pos/sales/detail` path is required — the host alone returns HTML, not JSON.

### 3. Turn on Pages

Repo → **Settings → Pages → Source → GitHub Actions**.

### 4. Build it

The workflow runs automatically on every push and **every 10 minutes**. To run it now:
**Actions → Publish Athar board → Run workflow**. About a minute later the board is live at:

```
https://<account>.github.io/<repo>/
```

Send that link to the branches once; it updates itself.

## Every month

Replace `data/master.xlsx` with the new month's workbook and push (or upload it in the
GitHub UI). The `data/**` path triggers a rebuild. Also update the countdown deadline in
`templates/race.html` (`DEADLINE` — currently end of October 2026).

## Notes

- **Actions minutes:** the 10-minute schedule is ~144 builds/day; each build pulls the
  month-to-date plus the same period last year. On a private repo that consumes paid-plan
  minutes — widen the `cron` in `publish.yml` (e.g. `*/30`) if you want to spend less.
- **Date range:** each build pulls from the 1st of the month to today. Today's sales count
  in totals; the pace/projection uses finished days only.
- **Local test before pushing:**

  ```bash
  python run.py --api --ref data/master.xlsx --out site
  ```

  Then open `site/index.html`. (`.env` supplies the URL and token locally.)
- **Branches with sales but no target** are printed as a warning at build time; add a target
  row in `data/master.xlsx` or an `EXCLUDE` entry in `athar/config.py` to clear them.
