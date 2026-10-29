# Athar (أثر) — business rules

These are the rules the code implements, as approved by Asmaa (October 2026). Where they differ from the program guide (Athar_Program_Launch_v1.3), these win.

The code sources of truth are `athar/config.py` (numbers) and `athar/rules.py` (allocation). The same logic is ported to `lovable/athar-rules.ts` and to the internal page's JavaScript.

## 1. Inputs

| File | How often | Layout |
|---|---|---|
| Odoo POS export | Daily | Pivot "Point of Sale Analysis", measure **Subtotal w/o discount**. Rows are a hierarchy shown by leading spaces in column A: 5 = company, 10 = branch, 15 = POS user. **Preferred:** one column per day (`01 Oct 2026` … ) plus a final `Total` column. The older single-total layout also works, but then you must pass `--asof`. |
| Monthly target | Once a month | Columns `# , Country, Region, City, Store, Target`. Target is in the country's own currency. |
| Program guide | Fixed | Background only. Not read by the code. |

- **Month-to-date files.** Each Odoo file is cumulative from the 1st of the month.
- **Excluded branch.** `EXBUAE` (a temporary UAE exhibition) is always excluded.
- **MATCH thresholds.** MATCH is not used: all branches are IBRAQ, so the MATCH minimums don't apply.

## 2. Currencies (never forget)

Sales and targets arrive in local currency. **Never add two currencies together.**

| Currency | To SAR |
|---|---|
| AED | 1.02 |
| BHD | 10 |
| OMR | 9.75 |
| KWD | 12.30 |
| QAR | 1.03 |

- **Achievement** = branch sales ÷ branch target, both in the same local currency.
- **Convert to SAR only** for company totals, the trend, the top-employee list and the car threshold.
- **Ignore Odoo's grand "Total" row**, because it mixes currencies.

## 3. Measures

- **Achievement:** sales ÷ target. 1.00 = 100%.
- **Projected (pace):** achievement ÷ (days elapsed ÷ days in month). The daily boards rank on this.
- **Official month-end result:** actual achievement ≥ 100%.

## 4. Prizes

- **Who qualifies:** branches at **≥ 100%**.
- **Car (A):** a company-wide race. It goes to the highest achievement among qualifiers with **≥ 300,000 SAR** sales (projected sales on the daily boards).
- **The other 40 prizes, split by market:**

| Market | Phone (B) | iPad (C) | Watch (D) | Gold bar (E) | Seats |
|---|---|---|---|---|---|
| UAE | 1st | – | – | 2nd | 2 |
| Oman | 1st | – | – | 2nd | 2 |
| Kuwait + Bahrain (one market) | 1st | – | – | 2nd | 2 |
| KSA | 7 | 10 | 10 | 7 | 34 |
| **Total** | **10** | **10** | **10** | **10** | **40** |

- **A vacant small-market seat goes to KSA only.** It goes to the next KSA qualifier after the 34, and a small market never gets more than its 2 seats. The vacant seat's prize type joins the KSA pool: the 34 quota holders are upgraded first, in rank order, and moved-in branches take the last prizes.
- **Not enough qualifiers:** the remaining prizes are **dropped**, not carried over.
- **One prize per branch.**
- **Winning employee:** the top seller on a *personal* POS account (pattern `1234-Name` or `Name-1234`). Shared or branch accounts are ignored. If one person has more than 60% of the branch's sales, the branch is flagged for review.
- **Car branch extras:** the 2nd employee gets a phone and the 3rd an iPad (both outside the 40). Everyone else gets a 250 SAR voucher if the branch hits 100%.
- **Cool-off periods (applied by hand at month end):** A 12 months, B 6, C 3, D 2, E none.

## 5. Public board («سباق أثر») — content rules

- **No amounts.** No money figure anywhere, not even an example like "1,000 → 1,400". Show percentages, ranks, names, and plain-word guidance with bars. The build fails if the public data contains `sales` or `target`.
- **Positive tone only.** Nobody is named as dropping out or falling. "Close to getting back in" replaces "left".
- **Internal-only content.** The full branch ranking, company-level negative stats, market cards and the month trend appear only on the internal board.
- **Branch picker:** alphabetical, grouped by country, so it doesn't reveal the ranking. An exact code match wins.
- **Employee names:** the guide (§11) requires consent (PDPL) before names go out widely.

## 6. Open points

- **Employees in several branches.** 47 employees sold in more than one branch. Each branch is currently counted on its own; a rule for choosing their main branch is pending.
- **"One prize per employee across branches"** is not implemented yet.
- **Tie-breaks** need data we don't have.
