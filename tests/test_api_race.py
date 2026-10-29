"""Unit check for api_race.aggregate (no network): GCC day boundary, counts, staff, EXCLUDE."""
import os
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from athar.api_race import aggregate                       # noqa: E402


def main():
    offset = datetime.timedelta(hours=3)                   # Asia/Riyadh = UTC+3
    orders = [
        # UTC 21:30 on Oct 4 -> GCC 00:30 Oct 5 (crosses the day boundary)
        {"date_order": "2026-10-04 21:30:00", "store_name": "A", "cashier_name": "2958-X", "amount_wod_incl_tax": 100},
        {"date_order": "2026-10-05 10:00:00", "store_name": "a", "cashier_name": "2958-X", "amount_wod_incl_tax": 50},
        {"date_order": "2026-10-05 12:00:00", "store_name": "B", "cashier_name": "4321-Y", "amount_wod_incl_tax": 40},
        {"date_order": "2026-10-05 12:00:00", "store_name": "EXBUAE", "cashier_name": "9-Z", "amount_wod_incl_tax": 999},
    ]
    daily, tx, staff, dom = aggregate(orders, offset)

    assert daily["2026-10-05"]["A"] == 150, "both A orders land on GCC Oct 5"
    assert "2026-10-04" not in daily, "nothing on Oct 4 after the +3h shift"
    assert tx["A"] == 2 and tx["B"] == 1, "transactions = order count"
    assert "EXBUAE" not in tx and "EXBUAE" not in daily, "excluded store dropped"
    assert staff["2958-X"]["tx"] == 2 and staff["2958-X"]["sales"] == 150
    assert staff["2958-X"]["daily"][5] == 150, "staff daily keyed by day of month"
    assert dom["A"][5] == 150, "store day-of-month totals for the last-year pull"
    print("OK test_api_race: GCC boundary, counts, staff and EXCLUDE all correct")


if __name__ == "__main__":
    main()
