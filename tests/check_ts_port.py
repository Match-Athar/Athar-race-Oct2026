"""Compare the TypeScript port (lovable/athar-rules.ts) with athar/rules.py on a real month file.

    python tests/check_ts_port.py data/pos.xlsx data/target.xlsx        (needs Node + `npx tsx`)
"""
import os
import sys
import json
import datetime
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from athar.readers import read_pos, read_targets  # noqa: E402
from athar.rules import allocate                   # noqa: E402
from athar.config import FX                        # noqa: E402
import calendar                                    # noqa: E402

pos, tgt = sys.argv[1:3]
asof = sys.argv[3] if len(sys.argv) > 3 else None
stores, daily = read_pos(pos)
targets = read_targets(tgt)
asof = asof or max(daily)
d = datetime.date.fromisoformat(asof)
frac = d.day / calendar.monthrange(d.year, d.month)[1]
sales = {k: v["sales"] for k, v in stores.items()}
rows = [{"code": k, "country": targets[k]["country"], "pct": s / targets[k]["target"] / frac,
         "sar": s * FX[targets[k]["country"]] / frac} for k, s in sales.items() if k in targets]
py = allocate(rows)

with tempfile.TemporaryDirectory() as tmp:
    inp = os.path.join(tmp, "in.json")
    json.dump({"sales": sales, "targets": targets, "asof": asof}, open(inp, "w"))
    script = os.path.join(tmp, "run.ts")
    open(script, "w").write(
        f'import {{ allocate, projectedRows }} from "{os.path.join(ROOT, "lovable", "athar-rules.ts")}";\n'
        f'import * as fs from "fs";\nconst d = JSON.parse(fs.readFileSync("{inp}", "utf8"));\n'
        'console.log(JSON.stringify(allocate(projectedRows(d.sales, d.targets, new Date(d.asof + "T00:00:00")))));\n')
    out = subprocess.run(["npx", "--yes", "tsx", script], capture_output=True, text=True, check=True).stdout
ts = json.loads(out)
same = ts["award"] == py["award"] and ts["car"] == py["car"] and ts["fill"] == py["fill"] and ts["moved"] == py["moved"]
print("TypeScript port matches Python:", same, "| prizes:", len(py["award"]), "| car:", py["car"])
sys.exit(0 if same else 1)
