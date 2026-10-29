# Rebuilding Athar as a live app (Supabase + Lovable)

Use this when you want a real web app: an admin uploads the Odoo file, and the public board updates for everyone automatically. The static pages in `site/` already work; this is the next step up.

## 1. Supabase (database)

1. Create a project at supabase.com.
2. Open **SQL Editor**, paste `supabase/schema.sql`, and run it.
3. Load a month's data:
   1. Run `python run.py --pos data/pos.xlsx --target data/target.xlsx --csv`.
   2. In **Table Editor**, import `site/csv/targets.csv` into `targets`, `daily_sales.csv` into `daily_sales`, and `user_sales_mtd.csv` into `user_sales_mtd`.
   3. Re-import the daily file each day; rows are keyed by date and store, so re-imports are safe.
4. Check: `select * from public_board order by rank_now limit 5;` should show percentages only.

**Security:**
- **Amounts stay protected.** The amounts live in the base tables, which only signed-in users can read.
- **The public page is anonymous.** It reads only `public_board` and `public_top_users`.
- **Narrow admin access.** Before going live, restrict the `authenticated` policies to your admin accounts.

Tested on Postgres 16 with the 13 Oct 2026 file: all 226 branches match the Python build exactly. That covers achievement, projected, rank, rank yesterday and today's change.

## 2. Lovable (app)

Create a Lovable project and connect it to the Supabase project. Then:

1. **Add the rules file.** Put `lovable/athar-rules.ts` into the project as `src/lib/athar-rules.ts`.
2. **Upload the reference page.** Attach `templates/public.html` and screenshots of the current board. The page is in Arabic and right-to-left.
3. **Paste this prompt:**

```text
Build "سباق أثر" — an Arabic, right-to-left, mobile-first public sales-race board for ~226 perfume
branches, reading from my connected Supabase project. Match the look and sections of the attached
public.html (dark trading-screen style).

DATA (read-only, anonymous):
- view public_board: month, asof, store, country, city, achievement, change_today, projected,
  car_eligible, rank_now, rank_prev   (achievement 1.0 = 100%)
- view public_top_users: store, pos (1..3), display_name
Never query any other table. The page must never show money amounts.

PRIZES: use allocate() from src/lib/athar-rules.ts (do not re-implement it). Build its input from
public_board for the latest month:
  { code: store, country, pct: projected, sar: car_eligible ? Infinity : 0 }
Result gives award per store (A=car, B=phone, C=iPad, D=watch, E=gold bar), seats filled per market,
and moved stores (mark them "منقولة").

SECTIONS, in this order:
1. News ticker «أخبار التأهيل», scrolling left→right as a seamless loop. Positive items only:
   🏁 crossed 100%, 🟢 entered the prizes, 🔼 upgraded, 🚀 top 3 jumps today (change_today),
   🔥 climbed ≥10 places (rank_prev - rank_now), 🎯 close to getting back in.
   Compare today's allocation with yesterday's: yesterday's achievement = achievement - change_today,
   yesterday's projected = that ÷ ((day of asof - 1) / days in month); run allocate() on it too.
2. «📍 فرعي» card: a searchable combobox (alphabetical, grouped by country; matches code, city,
   country, employee name; an exact code wins on Enter). Remember the choice in localStorage.
   Show today's %, projected %, status (🚗 car leader / ✅ in + prize / 🎯 not yet), rank change,
   top 3 employees, and what's needed in PLAIN WORDS + two bars (never numbers or %):
   "شوي بس فوق بيعكم المعتاد" / "زيادة بسيطة" / "زيادة واضحة" / "زيادة كبيرة" / "ضعف" / "أكثر من ضعف".
3. «🏁 حلبة السيارة»: top 4 car_eligible branches as lanes with 🚗 and a checkered line at 100%.
4. Four motivating stats: crossed 100%, branches in prize seats, branches one step away, days left.
5. «🚀 الأكثر صعوداً اليوم»: top 10 by change_today.
6. Prize board: per prize the top 3 with "عرض الكل"; show today's % and "متوقع X%"; a dashed gold row
   "🔓 X مقاعد شاغرة" for unfilled seats.
7. «🎯 على بُعد خطوة»: the next 12 branches after the last seat, with "+X نقطة وتدخل".
8. «كيف تفوز؟»: the rules text (copy from the attached page).
Fonts: Changa for numbers/headings, IBM Plex Sans Arabic for text. Wrap Latin user names in <bdi dir="ltr">.
```

4. **Add an admin page (optional).** Ask Lovable for: "an /admin page behind Supabase Auth with an Excel upload. Parse the Odoo pivot in the browser with SheetJS exactly like `athar/readers.py` (branch rows have 10 leading spaces and user rows 15; the day columns are titled `DD Mon YYYY`, followed by a Total column). Then upsert into `daily_sales`, `user_sales_mtd` and `targets`." Point it at `athar/readers.py` as the specification.

## 3. Keep the rules in one place

If a rule changes:

1. Change `athar/config.py` / `athar/rules.py`.
2. Mirror the change in `lovable/athar-rules.ts`.
3. Run `python tests/test_rules.py` and `python tests/check_ts_port.py data/pos.xlsx data/target.xlsx`. The second command confirms the TypeScript port gives identical prizes.
