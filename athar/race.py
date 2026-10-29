"""Build the data object (`D`) for the race-day board in templates/race.html.

This is a richer public board than build.public_data: per-store pace curves, a staff
directory, area league and a news ticker. It uses the design's own per-store prize model
(TIERS below, mirrored from the template's JS) — a store's "ceiling" is the best prize its
MATCH category allows, and prizes fill B/C/D/E seats by achievement.

`extra` (from master.read_master) lights up the Phase-2 fields; without it they stay neutral:
  names/ceiling/managers/curve  -> real store names, prize ceilings, area leaders, target curve
  tx + footfall                 -> store ATV index and conversion
  ly                            -> vs-last-year growth (store, area, company)
  staff                         -> staff ATV index, 7-day growth, and the hot/ATV star lists
Neutral defaults when a piece is missing: lyG / area.ly / staff.g7 = None, conv = None,
atvIdx = 0, staff.atvIdx = None, hot/atv = []. pulse.ly and store.atvIdx stay numeric because
the template reads them without a null guard.

Like public_data, the result carries only ratios, percentages, shares and names — never a raw
sales or target amount — so the page is safe to share.
"""
import re
import calendar
import datetime

from .config import FX, EMP_PATTERN

EMP_RE = re.compile(EMP_PATTERN)

# Prize tiers, mirrored from TIERS in templates/race.html. Ceiling comes from the master file's
# Prize column when present; otherwise it's inferred from projected monthly SAR via these minimums.
TIERS = [("A", 400_000), ("B", 200_000), ("C", 150_000), ("D", 100_000), ("E", 75_000)]
SLOTS = {"B": 10, "C": 10, "D": 10, "E": 10}          # prize seats per tier (A = the one car)
CAR_SAR = 400_000
CARFIELD_GAP = 0.5


def split_emp(raw):
    """'2958-Ahmed' / 'Aalzhrani-6563' -> ('2958','Ahmed'). ('', raw) when it has no number."""
    raw = raw.strip()
    m = re.match(r"^(\d{3,})\s*-\s*(.+)$", raw) or re.match(r"^(.+?)\s*-\s*(\d{3,})$", raw)
    if not m:
        return "", raw
    num, name = (m.group(1), m.group(2)) if m.group(1).isdigit() else (m.group(2), m.group(1))
    return num.strip(), name.strip()


def _infer_ceiling(proj_sar):
    for k, mn in TIERS:
        if proj_sar >= mn:
            return k
    return None


def _allocate(rows):
    """rows sorted by achievement desc. Set prize/zone in place: car = top eligible A-ceiling store,
    the rest fill B/C/D/E seats, each taking the best tier its ceiling allows with a free seat."""
    elig = [s for s in rows if s["ach"] >= 1 and s["ceiling"]]
    car = next((s for s in elig if s["ceiling"] == "A"), None)
    if car:
        car["prize"] = "A"
    slots, order = dict(SLOTS), "BCDE"
    for s in elig:
        if s is car:
            continue
        start = s["ceiling"] if s["ceiling"] in order else "B"
        for k in order[order.index(start):]:
            if slots[k] > 0:
                s["prize"] = k
                slots[k] -= 1
                break
    for s in rows:
        s["zone"] = "in" if s.get("prize") else ("near" if s["ach"] >= 0.85 else "out")


def race_data(stores, daily, targets, asof, elapsed=None, extra=None):
    e = extra or {}
    names, ceil_map, managers = e.get("names", {}), e.get("ceiling", {}), e.get("managers", {})
    curve, tx, foot = e.get("curve"), e.get("tx", {}), e.get("footfall", {})
    ly, staff_ex = e.get("ly", {}), e.get("staff", {})

    d0 = datetime.date.fromisoformat(asof)
    dim = calendar.monthrange(d0.year, d0.month)[1]
    lastday = d0.day
    de = elapsed or lastday
    frac = de / dim
    L, left = lastday - 1, dim - lastday
    sar = lambda code, v: v * FX[targets[code]["country"]]

    def day_sales(code, d):
        return daily.get(datetime.date(d0.year, d0.month, d).isoformat(), {}).get(code, 0.0)

    cum = {k: [] for k in targets}
    for k in targets:
        run = 0.0
        for d in range(1, lastday + 1):
            run += day_sales(k, d)
            cum[k].append(round(run, 2))

    # company ATV baseline (SAR per transaction) for the atvIdx figures
    company_atv = 0.0
    if tx:
        tt = sum(tx.get(k, 0) for k in targets)
        if tt:
            company_atv = sum(sar(k, cum[k][-1] if cum[k] else 0) for k in targets) / tt

    def ly_mtd(code):
        return sum(v for d, v in ly.get(code, {}).items() if d <= lastday)

    rows, staff = [], {}
    for code, t in targets.items():
        tgt, fx = t["target"], FX[t["country"]]
        mtd = cum[code][-1] if cum[code] else 0.0
        ach = mtd / (tgt * frac) if tgt and frac else 0.0
        proj_sar = mtd * fx / frac if frac else 0.0
        ceiling = ceil_map[code] if code in ceil_map else _infer_ceiling(proj_sar)

        ca = [round(c / tgt * 100, 2) for c in cum[code]] if tgt else [0.0] * lastday
        ct = [round(x, 2) for x in curve] if curve and len(curve) == dim else \
             [round((i + 1) / dim * 100, 2) for i in range(dim)]
        end = round(ach * 100, 2)
        pj = [round(ca[L] + (end - ca[L]) * j / left, 2) for j in range(left + 1)] if left else [end]

        dtar = tgt / dim if tgt else 0.0
        win = lambda a, b: sum(day_sales(code, d) for d in range(max(1, a), b + 1))
        day = day_sales(code, lastday)
        s3, s7, sp7 = win(lastday - 2, lastday), win(lastday - 6, lastday), win(lastday - 13, lastday - 7)
        dayAch = day / dtar if dtar else 0.0
        ach3 = s3 / (3 * dtar) if dtar else 0.0
        ach7 = s7 / (7 * dtar) if dtar else 0.0
        accel = ach7 - (sp7 / (7 * dtar) if dtar else 0.0)

        r3, remain = s3 / 3, tgt - mtd
        if remain <= 0 or left <= 0:
            needUp = None
        elif r3 <= 0:
            needUp = 9.99
        else:
            needUp = remain / left / r3 - 1

        steps = []
        for delta in range(-30, 55, 5):
            rate = r3 * (1 + delta / 100)
            pa = (mtd + rate * left) / tgt if tgt else 0.0
            steps.append([delta, round(pa, 4), (ceiling if pa >= 1 and ceiling else None)])

        emps = sorted(([u[0], float(u[1])] for u in stores.get(code, {}).get("users", [])
                       if EMP_RE.search(str(u[0]).strip())), key=lambda u: -u[1])
        stot = stores.get(code, {}).get("sales", 0.0) or sum(e2[1] for e2 in emps) or 1.0
        top_sales = emps[0][1] if emps else 1.0
        team = []
        for pos, (raw, es) in enumerate(emps, 1):
            num, name = split_emp(raw)
            share = round(es / stot, 4) if stot else 0.0
            sx = staff_ex.get(raw, {})
            team.append([name, num, pos, share, raw])
            staff[raw] = {"name": name, "id": num, "store": code, "rank": pos, "of": len(emps),
                          "share": share, "ofTop": round(es / top_sales, 4) if top_sales else 0.0,
                          "g7": _g7(sx.get("daily"), lastday), "atvIdx": _atv(sx, fx, company_atv),
                          "_tx": sx.get("tx", 0)}

        atvIdx = 0
        if tx.get(code) and company_atv:
            atvIdx = round((sar(code, mtd) / tx[code]) / company_atv - 1, 4)
        lymtd = ly_mtd(code)
        rows.append({
            "code": code, "name": names.get(code) or t.get("name") or code, "city": t["city"],
            "am": managers.get(code) or t["region"], "region": t["region"], "ceiling": ceiling,
            "ach": round(ach, 4), "lyG": round((mtd - lymtd) / lymtd, 4) if lymtd > 0 else None,
            "dayAch": round(dayAch, 4), "ach3": round(ach3, 4), "ach7": round(ach7, 4),
            "accel": round(accel, 4), "conv": round(tx[code] / foot[code], 4) if foot.get(code) and tx.get(code) else None,
            "needUp": None if needUp is None else round(needUp, 4),
            "ca": ca, "ct": ct, "pj": pj, "steps": steps, "team": team, "prize": None,
            "atvIdx": atvIdx, "carOk": proj_sar >= CAR_SAR,
            "carGap": round(max(0.0, CAR_SAR / proj_sar - 1), 4) if proj_sar > 0 else 9.99,
            "carField": False, "nextTier": None,
        })

    rows.sort(key=lambda s: -s["ach"])
    for i, s in enumerate(rows, 1):
        s["rank"] = i
        s["carField"] = (s["ceiling"] == "A") if ceil_map else (s["carOk"] or s["carGap"] <= CARFIELD_GAP)
    _allocate(rows)
    for s in staff.values():
        s.pop("_tx", None)

    by = {s["code"]: s for s in rows}
    tot_s = sum(sar(s["code"], cum[s["code"]][-1] if cum[s["code"]] else 0) for s in rows)
    tot_t = sum(targets[s["code"]]["target"] * FX[targets[s["code"]]["country"]] for s in rows)
    pulse = {"ach": round(tot_s / (tot_t * frac), 4) if tot_t and frac else 0.0,
             "monthPct": round(tot_s / tot_t, 4) if tot_t else 0.0, "ly": _group_ly(rows, targets, cum, ly, lastday, sar),
             "inz": sum(1 for s in rows if s["prize"]), "near": sum(1 for s in rows if s["zone"] == "near"),
             "n": len(rows)}

    areas = _areas(rows, targets, cum, ly, lastday, frac, sar, managers)
    tops = sorted(staff.items(), key=lambda kv: -kv[1]["share"])[:8]
    top = [[raw, p["name"], p["id"], p["store"], p["share"]] for raw, p in tops]
    hots = sorted(((raw, p) for raw, p in staff.items() if p["g7"] is not None), key=lambda kv: -kv[1]["g7"])[:8]
    hot = [[raw, p["name"], p["id"], p["store"], p["g7"]] for raw, p in hots]
    atvs = sorted(((raw, p) for raw, p in staff.items()
                   if p["atvIdx"] is not None and staff_ex.get(raw, {}).get("tx", 0) >= 60),
                  key=lambda kv: -kv[1]["atvIdx"])[:8]
    atv = [[raw, p["name"], p["id"], p["store"], p["atvIdx"]] for raw, p in atvs]

    news = _news(rows, by, cum, targets, d0, dim, de, L, top)
    for s in rows:
        s.pop("region", None)
    return {"asOf": asof, "last": L, "days": dim, "left": left, "pulse": pulse, "areas": areas,
            "stores": rows, "staff": staff, "top": top, "hot": hot, "atv": atv, "news": news}


def _g7(sd, lastday):
    """7-day growth: last 7 days vs the 7 before, from a {day: sales} map. None if too early/no base."""
    if not sd or lastday < 14:
        return None
    last7 = sum(sd.get(d, 0) for d in range(lastday - 6, lastday + 1))
    prev7 = sum(sd.get(d, 0) for d in range(lastday - 13, lastday - 6))
    return round(last7 / prev7 - 1, 4) if prev7 > 0 else None


def _atv(sx, fx, company_atv):
    """Staff ATV index vs the company average. None without transaction data."""
    txn, sales = sx.get("tx", 0), sx.get("sales", 0)
    if not txn or not company_atv:
        return None
    return round((sales * fx / txn) / company_atv - 1, 4)


def _group_ly(rows, targets, cum, ly, lastday, sar):
    """Like-for-like company growth vs last year (0 when no last-year data)."""
    ty = sum(sar(s["code"], cum[s["code"]][-1] if cum[s["code"]] else 0) for s in rows if s["code"] in ly)
    lv = sum(sar(s["code"], sum(v for d, v in ly[s["code"]].items() if d <= lastday)) for s in rows if s["code"] in ly)
    return round((ty - lv) / lv, 4) if lv > 0 else 0


def _areas(rows, targets, cum, ly, lastday, frac, sar, managers):
    """One row per area manager (the design's area league), outside the competition."""
    ach_of = {s["code"]: s["ach"] for s in rows}
    areas = {}
    for s in rows:
        am = s["am"]
        a = areas.setdefault(am, {"s": 0.0, "t": 0.0, "n": 0, "inz": 0, "near": 0, "best": None,
                                  "tyl": 0.0, "lyl": 0.0})
        a["s"] += sar(s["code"], cum[s["code"]][-1] if cum[s["code"]] else 0)
        a["t"] += targets[s["code"]]["target"] * FX[targets[s["code"]]["country"]]
        a["n"] += 1; a["inz"] += bool(s["prize"]); a["near"] += s["zone"] == "near"
        if s["code"] in ly:
            a["tyl"] += sar(s["code"], cum[s["code"]][-1] if cum[s["code"]] else 0)
            a["lyl"] += sar(s["code"], sum(v for d, v in ly[s["code"]].items() if d <= lastday))
        if a["best"] is None or s["ach"] > ach_of[a["best"]]:
            a["best"] = s["code"]
    out = [{"ach": round(a["s"] / (a["t"] * frac), 4) if a["t"] and frac else 0.0,
            "monthPct": round(a["s"] / a["t"], 4) if a["t"] else 0.0,
            "ly": round((a["tyl"] - a["lyl"]) / a["lyl"], 4) if a["lyl"] > 0 else None,
            "inz": a["inz"], "near": a["near"], "n": a["n"], "am": am, "best": a["best"]}
           for am, a in areas.items()]
    return sorted(out, key=lambda x: -x["ach"])


def _news(rows, by, cum, targets, d0, dim, de, L, top):
    """Positive movement vs yesterday: day jumps, climbers, prize entries/exits, tier changes."""
    if de <= 1 or L < 1:
        return {"day": L, "entered": 0, "dropped": 0, "items": []}
    pf = (de - 1) / dim
    prev = []
    for s in rows:
        code = s["code"]; t = targets[code]; fx = FX[t["country"]]
        psales = cum[code][L - 1] if len(cum[code]) > L - 1 else 0.0
        pach = psales / (t["target"] * pf) if t["target"] and pf else 0.0
        prev.append({"code": code, "ach": pach, "ceiling": s["ceiling"], "prize": None, "zone": None})
    prev.sort(key=lambda s: -s["ach"])
    prank = {s["code"]: i + 1 for i, s in enumerate(prev)}
    _allocate(prev)
    pprize = {s["code"]: s["prize"] for s in prev}

    items, entered, dropped, jumped = [], 0, 0, set()
    gains = sorted(({"code": s["code"], "g": round(by[s["code"]]["ca"][L] - by[s["code"]]["ca"][L - 1], 1),
                     "mv": prank[s["code"]] - s["rank"]} for s in rows), key=lambda x: -x["g"])
    for g in gains[:5]:
        if g["g"] <= 0:
            break
        jumped.add(g["code"])
        items.append({"k": "jump", "store": g["code"], "pts": g["g"], "rank": by[g["code"]]["rank"], "mv": max(0, g["mv"])})
    for s in rows:
        now, was = s["prize"], pprize.get(s["code"])
        if now and not was:
            entered += 1; items.append({"k": "in", "store": s["code"], "tier": now, "rank": s["rank"]})
        elif was and not now:
            dropped += 1; items.append({"k": "out", "store": s["code"], "was": was, "rank": s["rank"]})
        elif now and was and now != was:
            items.append({"k": "tier", "store": s["code"], "tier": now, "was": was})
    for mv, s in sorted(((prank[s["code"]] - s["rank"], s) for s in rows if s["code"] not in jumped), key=lambda x: -x[0])[:4]:
        if mv < 3:
            break
        items.append({"k": "climb", "store": s["code"], "mv": mv, "rank": s["rank"]})
    for raw, name, num, store, _ in top[:3]:
        items.append({"k": "star", "raw": raw, "name": name, "id": num, "store": store, "pos": 1})
    return {"day": L, "entered": entered, "dropped": dropped, "items": items}
