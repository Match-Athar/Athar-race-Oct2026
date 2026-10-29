"""Smoke/invariant check for athar.race.race_data against the real inputs in data/.

Run: python tests/test_race.py   (skips cleanly if data/pos.xlsx or data/target.xlsx is missing)
Checks the D contract the race.html template relies on, so a broken generator fails here,
not silently in the browser."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from athar.readers import read_pos, read_targets      # noqa: E402
from athar.race import race_data, SLOTS               # noqa: E402


def main():
    pos = os.path.join(ROOT, "data", "pos.xlsx")
    tgt = os.path.join(ROOT, "data", "target.xlsx")
    if not (os.path.exists(pos) and os.path.exists(tgt)):
        print("SKIP test_race: data/pos.xlsx or data/target.xlsx not found")
        return
    stores, daily = read_pos(pos)
    targets = read_targets(tgt)
    asof = max(daily) if daily else None
    assert asof, "need day columns in the POS export"
    D = race_data(stores, daily, targets, asof)

    for k in ("asOf", "last", "days", "left", "pulse", "areas", "stores", "staff", "top", "hot", "atv", "news"):
        assert k in D, f"missing top-level key {k}"
    rows = D["stores"]
    assert len(rows) == len(targets), "one row per target store"
    assert [s["rank"] for s in rows] == list(range(1, len(rows) + 1)), "ranks are 1..n in order"
    assert all(rows[i]["ach"] >= rows[i + 1]["ach"] for i in range(len(rows) - 1)), "sorted by achievement desc"

    import collections
    pc = collections.Counter(s["prize"] for s in rows if s["prize"])
    assert pc.get("A", 0) <= 1, "at most one car"
    for k, n in SLOTS.items():
        assert pc.get(k, 0) <= n, f"tier {k} within its {n} seats"
    assert all(s["zone"] == "in" for s in rows if s["prize"]), "prized stores are in-zone"
    assert D["pulse"]["inz"] == sum(1 for s in rows if s["prize"]), "pulse.inz counts prizes"

    for s in rows:
        assert len(s["ca"]) == D["last"] + 1, f"{s['code']}: ca length"
        assert len(s["pj"]) == D["left"] + 1, f"{s['code']}: pj length"
        assert len(s["ct"]) == D["days"], f"{s['code']}: ct length"
        assert any(step[0] == 0 for step in s["steps"]), f"{s['code']}: calc has a 0% step"
        assert isinstance(s["atvIdx"], (int, float)), "atvIdx must be numeric (not null-safe in template)"
    assert isinstance(D["pulse"]["ly"], (int, float)), "pulse.ly must be numeric (not null-safe in template)"

    print(f"OK test_race: {len(rows)} stores, {len(D['staff'])} staff, {len(D['areas'])} areas, "
          f"prizes {dict(pc)}, news {len(D['news']['items'])} items")


if __name__ == "__main__":
    main()
