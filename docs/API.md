# Driving the race board from the Odoo API

The race board reads **all transactional data** (store sales, transaction counts, staff
performance, and last-year sales) from one Odoo POS orders endpoint. The **non-transactional
reference data** (targets, the daily target curve, prize ceilings, store names, area managers,
footfall) is **not** in POS orders, so it is supplied from the master workbook via `--ref`.

```bash
python run.py --api --ref "MATCH Sales Dashboard October 2026.xlsx" --out site
# live, auto-refreshing:
python run.py --api --ref "...xlsx" --serve --every 5
```

Code: `athar/api_race.py` (the client + aggregation), wired in `run.py` via `--api --ref`.

---

## 1. Settings (`.env` or CI secrets)

| Variable | Required | Meaning |
|---|---|---|
| `ODOO_API_URL` | ✅ | the orders endpoint (no query string) |
| `ODOO_API_TOKEN` | ✅ | Bearer token |
| `ODOO_TZ` | optional | GCC timezone for day boundaries. Default `Asia/Riyadh` (UTC+3). Dubai/Muscat = UTC+4 |

## 2. Request

```
GET {ODOO_API_URL}?date_from=YYYY-MM-DD HH:MM:SS&date_to=YYYY-MM-DD HH:MM:SS&limit=2000&offset=N
Authorization: Bearer {ODOO_API_TOKEN}
Accept: application/json
```

- `date_from` / `date_to` are **UTC** datetimes (inclusive). The board works in GCC time and
  converts: the GCC day `2026-10-05` is requested as `2026-10-04 21:00:00 .. 2026-10-05 20:59:59`
  (UTC+3).
- `limit` ≤ 2000, `offset` pages through the result; keep fetching while `meta.has_more` is true.
- The board makes **two calls** (same endpoint, different ranges):
  1. **Month-to-date:** 1st of the month 00:00 → end of `--asof` (default today), GCC.
  2. **Same period last year:** the same day-range in the previous year (for vs-last-year growth).
     If the API returns nothing for last year, growth is simply left blank — not an error.

## 3. Expected response

```json
{
  "success": true,
  "data": [
    {
      "date_order": "2026-10-05 11:35:21",
      "store_name": "MUBARKIA",
      "order_name": "MUBARKIA/31329",
      "cashier_name": "5580-AAbbas",
      "amount_wod_excl_tax": 16.25,
      "amount_wod_incl_tax": 16.25
    }
  ],
  "meta": { "total": 48213, "limit": 2000, "offset": 0, "count": 2000, "has_more": true }
}
```

**One row per POS order.** Refunds are negative rows (they net off). Fields the board uses:

| Field | Type | Used for |
|---|---|---|
| `date_order` | `"YYYY-MM-DD HH:MM:SS"` **UTC** | grouping into the correct GCC day |
| `store_name` | string | store code (upper-cased; `EXBUAE` is excluded) |
| `cashier_name` | string | staff — personal accounts like `5580-AAbbas` (pattern `\d{3,}-name`); store accounts are ignored for staff rankings |
| `amount_wod_incl_tax` | number | **sales** (tax-included, to match the targets' basis); summed per store/day/staff |
| `amount_wod_excl_tax` | number | ex-VAT amount; not used by the race board |
| `meta.has_more` | bool | paging — keep requesting until false |

On failure, return `{"success": false, "message": "..."}` (or `error`); the build reports it and
keeps the previous page.

### What the board derives from these rows
- **Store sales / day** — sum `amount_wod_incl_tax` (tax-included) by `store_name` + GCC day.
- **Transactions** — **count of order rows** per store (and per staff). No separate field needed.
- **ATV** — sales ÷ transactions (store and staff, vs the company average).
- **Staff performance** — group by `cashier_name`: MTD sales, transaction count, and per-day sales
  (for the 7-day growth figure).
- **Last-year growth** — the second (previous-year) pull, compared like-for-like.

## 4. Data the orders API does NOT contain (comes from `--ref`)

These are not sales rows, so they are read from the master workbook (or your own endpoints later):

| Data | Sheet in the master workbook |
|---|---|
| Targets + **daily target curve** | `TY Sales Target` (31 daily cells; October target = their sum) |
| **Prize ceiling** per store (A–E) | `TY Sales Target` → `Prize` (Car→A, Smart Phone→B, I Pad→C, Smart Watch→D, Gold Bar→E) |
| Store **name / city / region** | `TY Sales Target` |
| **Area managers** | `TY Sales Target` → `Area Leader` |
| **Footfall** (for conversion) | `Footfall` |

If you later expose endpoints for targets and footfall, replace `read_master(ref_path)` in
`athar/api_race.py` with calls to them — nothing else in the board changes.

## 5. Notes
- `shortcut: api_race fetches the whole month each run (no per-day cache like api.py); add day
  caching if the month gets heavy or --every is frequent.`
- Amounts in each country's own currency; converted to SAR via `config.FX` only where needed
  (car threshold, ATV, company/area roll-ups). Never add two currencies before converting.
