"""Run:  python -m pytest -q      (or simply:  python tests/test_rules.py)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from athar.rules import allocate  # noqa: E402


def br(code, country, pct, sar=100_000):
    return {"code": code, "country": country, "pct": pct, "sar": sar}


def ksa(n, start=1.50, step=0.001):
    return [br(f"K{i:02d}", "KSA", start - i * step) for i in range(n)]


def test_car_is_company_wide_and_needs_300k():
    rows = [br("BIG", "UAE", 1.20, 400_000), br("SMALL", "KSA", 1.90, 50_000)] + ksa(5)
    r = allocate(rows)
    assert r["car"] == "BIG"                      # SMALL is higher but under 300k SAR
    assert r["award"]["BIG"] == "A"
    assert r["award"]["SMALL"] == "B"             # best KSA branch gets the first phone


def test_small_markets_get_phone_then_gold():
    rows = [br("U1", "UAE", 1.3), br("U2", "UAE", 1.2), br("U3", "UAE", 1.1),
            br("O1", "Oman", 1.05), br("KW1", "Kuwait", 1.02), br("BH1", "Bahrain", 1.01)] + ksa(34)
    r = allocate(rows)
    assert r["award"]["U1"] == "B" and r["award"]["U2"] == "E"
    assert "U3" not in r["award"]                  # a small market never gets more than 2
    assert r["award"]["O1"] == "B"
    assert r["award"]["KW1"] == "B" and r["award"]["BH1"] == "E"   # Kuwait + Bahrain share one market


def test_vacant_small_seats_move_to_ksa_and_moved_branches_get_the_last_prizes():
    rows = [br("O1", "Oman", 1.4), br("O2", "Oman", 1.3)] + ksa(45)
    r = allocate(rows)
    assert r["moved"] == [f"K{i:02d}" for i in range(34, 38)]   # 4 vacant seats (UAE 2 + KW-BH 2)
    counts = {c: list(r["award"].values()).count(c) for c in "BCDE"}
    assert counts == {"B": 10, "C": 10, "D": 10, "E": 10}
    assert all(r["award"][k] == "E" for k in r["moved"])        # last in the queue
    assert "K38" not in r["award"]


def test_prizes_drop_when_not_enough_qualifiers():
    rows = ksa(5) + [br("LOW", "KSA", 0.99)]
    r = allocate(rows)
    assert len(r["award"]) == 5 and "LOW" not in r["award"]
    assert sorted(r["award"].values()) == ["B"] * 5


def test_one_prize_per_branch():
    rows = [br("BIG", "KSA", 2.0, 900_000)] + ksa(60)
    r = allocate(rows)
    assert list(r["award"]).count("BIG") == 1 and r["award"]["BIG"] == "A"
    assert len(r["award"]) == 1 + 34 + 6           # car + KSA quota + the 6 vacant small seats


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
