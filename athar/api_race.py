"""Live race board from the Odoo POS orders API.

Everything transactional comes from the orders endpoint (the same one api.py already uses),
read across two date ranges:
    this month-to-date   -> store/day sales, store transaction counts, staff sales+counts+daily
    same period last year -> per-store last-year sales (for the vs-last-year growth)

The NON-transactional reference data — targets, the daily target curve, prize ceilings, store
names, area managers and footfall — is not in POS orders, so it is read from the master
workbook (`ref_path`). If you later expose dedicated endpoints for those, replace read_master
here; nothing else changes. See docs/API.md for the exact request and response contract.

read_race_api() returns (stores, daily, targets, asof, extra) in the shape race.race_data expects.
"""
import os
import datetime

from .api import load_env, gcc_offset, fetch_orders, UTC_FMT
from .config import EXCLUDE


def aggregate(orders, offset):
    """orders -> (daily, store_tx, staff, store_dom). GCC day = order UTC time + offset.

    daily      {YYYY-MM-DD: {STORE: sales}}         store sales per GCC day
    store_tx   {STORE: count}                       transactions (= order rows) per store
    staff      {cashier: {store, sales, tx, daily{day_of_month: sales}}}
    store_dom  {STORE: {day_of_month: sales}}       used for the last-year pull
    """
    daily, store_tx, staff, dom = {}, {}, {}, {}
    for i, o in enumerate(orders):
        try:
            store = str(o["store_name"]).strip().upper()
            raw = str(o.get("cashier_name") or "").strip()
            amt = float(o.get("amount_wod_incl_tax") or 0)   # tax-included, to match the targets' basis
            g = datetime.datetime.strptime(o["date_order"], UTC_FMT) + offset
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Sales API order {i} is invalid ({e}): {o}") from None
        if not store or store in EXCLUDE:
            continue
        iso, d = g.date().isoformat(), g.day
        daily.setdefault(iso, {})[store] = daily.get(iso, {}).get(store, 0) + amt
        store_tx[store] = store_tx.get(store, 0) + 1
        sd = dom.setdefault(store, {})
        sd[d] = sd.get(d, 0) + amt
        if raw:
            s = staff.setdefault(raw, {"store": store, "sales": 0.0, "tx": 0, "daily": {}})
            s["sales"] += amt
            s["tx"] += 1
            s["daily"][d] = s["daily"].get(d, 0) + amt
    for sd in daily.values():
        for k in sd:
            sd[k] = round(sd[k], 2)
    for s in staff.values():
        s["sales"] = round(s["sales"], 2)
    return daily, store_tx, staff, dom


def _range(start, end, offset):
    """GCC [start 00:00 .. end 23:59:59] as the UTC datetimes the API expects."""
    uf = datetime.datetime.combine(start, datetime.time()) - offset
    ut = datetime.datetime.combine(end, datetime.time()) + datetime.timedelta(days=1, seconds=-1) - offset
    return uf, ut


def read_race_api(ref_path, asof=None):
    from .master import read_master                      # reference data (targets, footfall, curve, ...)

    load_env()
    url = os.environ.get("ODOO_API_URL", "").strip()
    token = os.environ.get("ODOO_API_TOKEN", "").strip()
    if not url or not token or "your-" in url + token:
        raise ValueError("Fill in ODOO_API_URL and ODOO_API_TOKEN in .env")
    tz = os.environ.get("ODOO_TZ") or "Asia/Riyadh"
    offset = gcc_offset(tz)
    today = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + offset).date()
    end = datetime.date.fromisoformat(asof) if asof else today
    start = end.replace(day=1)

    uf, ut = _range(start, end, offset)
    print(f"Sales API: {start} .. {end} ({tz}, sent in UTC)", flush=True)
    daily, store_tx, staff, _ = aggregate(fetch_orders(url, token, uf, ut), offset)
    if not daily:
        raise ValueError(f"The sales API returned no orders for {start} .. {end}")
    asof_iso = max(daily)

    try:                                                 # same period last year -> growth; optional
        luf, lut = _range(start.replace(year=start.year - 1), end.replace(year=end.year - 1), offset)
        _, _, _, ly_dom = aggregate(fetch_orders(url, token, luf, lut), offset)
    except Exception as e:
        print(f"  (no last-year data from the API: {e}; growth will be blank)", flush=True)
        ly_dom = {}

    stores = {}
    for sd in daily.values():
        for st, v in sd.items():
            stores.setdefault(st, {"sales": 0.0, "users": []})["sales"] += v
    for st, s in stores.items():
        s["sales"] = round(s["sales"], 2)
    for raw, s in staff.items():
        if s["store"] in stores:
            stores[s["store"]]["users"].append([raw, s["sales"]])

    _, _, targets, _, ref = read_master(ref_path)        # targets + non-transactional reference only
    extra = {"names": ref["names"], "ceiling": ref["ceiling"], "managers": ref["managers"],
             "curve": ref["curve"], "footfall": ref["footfall"],
             "tx": store_tx, "ly": ly_dom, "staff": staff}
    return stores, daily, targets, asof_iso, extra
