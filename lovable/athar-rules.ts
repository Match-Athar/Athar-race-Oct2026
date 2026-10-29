/**
 * Athar (أثر) prize rules — TypeScript port of athar/rules.py, for a Lovable / React / Supabase app.
 * Keep the two files identical in behaviour (tests/check_ts_port.py compares them on real data).
 *
 * Inputs are per-branch, month-to-date, in LOCAL currency. Never add two currencies together.
 */

export const FX: Record<string, number> = { KSA: 1.0, UAE: 1.02, Oman: 9.75, Kuwait: 12.3, Bahrain: 10.0, Qatar: 1.03 };
export const MARKET: Record<string, string> = { KSA: "KSA", UAE: "UAE", Oman: "Oman", Kuwait: "KW-BH", Bahrain: "KW-BH", Qatar: "Qatar" };
export const QUOTA: Record<string, number> = { KSA: 34, UAE: 2, Oman: 2, "KW-BH": 2 };
export const SMALL_MARKETS = ["UAE", "Oman", "KW-BH"] as const;
export const PER_CATEGORY = 10;
export const CAR_MIN_SAR = 300_000;
export const EXCLUDE = new Set(["EXBUAE"]);
export const EMP_RE = /(^\d{3,}\s*-)|(-\s*\d{3,}$)/;
export const PRIZE: Record<Prize, string> = { A: "سيارة", B: "جوال ذكي", C: "آيباد", D: "ساعة ذكية", E: "سبيكة ذهب" };

export type Prize = "A" | "B" | "C" | "D" | "E";
export interface Ranked { code: string; country: string; pct: number; sar: number }
export interface Allocation { award: Record<string, Prize>; car: string | null; fill: Record<string, number>; moved: string[] }

/** pct: achievement used for ranking (1 = 100%); sar: sales in SAR for the car threshold. */
export function allocate(branches: Ranked[]): Allocation {
  const elig = branches.filter(b => b.pct >= 1).sort((a, b) => b.pct - a.pct);
  const award: Record<string, Prize> = {};
  const car = elig.find(b => b.sar >= CAR_MIN_SAR) ?? null;
  if (car) award[car.code] = "A";
  const rest = elig.filter(b => b !== car);
  const mkt = (b: Ranked) => MARKET[b.country];

  const fill: Record<string, number> = {};
  const used = { B: 0, E: 0 };
  let smallSeats = 0;
  for (const m of SMALL_MARKETS) {
    const lst = rest.filter(b => mkt(b) === m).slice(0, QUOTA[m]);
    fill[m] = lst.length; smallSeats += lst.length;
    lst.forEach((b, i) => { const c = i === 0 ? "B" : "E"; award[b.code] = c; used[c]++; });
  }
  const ksaAll = rest.filter(b => mkt(b) === "KSA");
  const ksa = ksaAll.slice(0, QUOTA.KSA);
  fill.KSA = ksa.length;
  const vacant = SMALL_MARKETS.reduce((s, m) => s + QUOTA[m], 0) - smallSeats;
  const moved = ksaAll.slice(QUOTA.KSA, QUOTA.KSA + vacant);   // vacant small seats go to KSA only

  const pool = [...ksa, ...moved];                               // moved-in branches take the last prizes
  const seq: Prize[] = [
    ...Array(PER_CATEGORY - used.B).fill("B"), ...Array(PER_CATEGORY).fill("C"),
    ...Array(PER_CATEGORY).fill("D"), ...Array(PER_CATEGORY - used.E).fill("E"),
  ];
  pool.forEach((b, i) => { if (i < seq.length) award[b.code] = seq[i]; });
  return { award, car: car ? car.code : null, fill, moved: moved.map(b => b.code) };
}

/** Convenience: build the ranked rows from month-to-date sales and targets (both local currency). */
export function projectedRows(
  sales: Record<string, number>,
  targets: Record<string, { country: string; target: number }>,
  asof: Date,
): Ranked[] {
  const dim = new Date(asof.getFullYear(), asof.getMonth() + 1, 0).getDate();
  const frac = asof.getDate() / dim;
  return Object.entries(sales)
    .filter(([k]) => targets[k] && !EXCLUDE.has(k))
    .map(([k, s]) => {
      const t = targets[k];
      return { code: k, country: t.country, pct: t.target ? s / t.target / frac : 0, sar: (s * FX[t.country]) / frac };
    });
}
