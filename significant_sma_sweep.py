from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"


@dataclass(frozen=True)
class SetupMetric:
    sma: int
    buy: int
    sell: int
    avg_rank_pct: float
    median_rank_pct: float
    top_10_rate: float
    top_25_rate: float
    avg_cagr: float
    median_cagr: float
    p25_cagr: float
    avg_dd: float
    worst_dd: float
    beat_200_5_3_rate: float
    score: float


def read_prices(path: str) -> dict[datetime, float]:
    with Path(path).open(newline="") as f:
        return {
            datetime.strptime(row["Date"], "%m/%d/%Y %H:%M:%S"): float(row["Close"])
            for row in csv.DictReader(f, delimiter="\t")
        }


def rolling_sma(values: list[float], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    total = 0.0
    for i, value in enumerate(values):
        total += value
        if i >= length:
            total -= values[i - length]
        if i >= length - 1:
            out[i] = total / length
    return out


def simulate_equity(
    qqq: list[float],
    tqqq: list[float],
    sma_values: list[float | None],
    buy: int,
    sell: int,
    cash_yield: float = 0.04,
) -> list[float]:
    invested = False
    equity = [1.0]
    cash_daily = cash_yield / 252.0
    for i in range(1, len(qqq)):
        signal_idx = i - 1
        sma = sma_values[signal_idx]
        if sma is not None:
            close = qqq[signal_idx]
            if not invested and close > sma * (1 + buy / 100):
                invested = True
            elif invested and close < sma * (1 - sell / 100):
                invested = False
        day_return = tqqq[i] / tqqq[i - 1] - 1 if invested else cash_daily
        equity.append(equity[-1] * (1 + day_return))
    return equity


def max_drawdown_segment(equity: list[float], start: int, end: int) -> float:
    peak = equity[start]
    worst = 0.0
    for value in equity[start : end + 1]:
        if value > peak:
            peak = value
        dd = value / peak - 1.0
        if dd < worst:
            worst = dd
    return worst


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    idx = int((len(values) - 1) * p)
    return values[idx]


def add_years(dt: datetime, years: int) -> datetime:
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        return dt.replace(year=dt.year + years, day=28)


def first_index_on_or_after(dates: list[datetime], target: datetime) -> int | None:
    lo, hi = 0, len(dates) - 1
    result = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if dates[mid] >= target:
            result = mid
            hi = mid - 1
        else:
            lo = mid + 1
    return result


def monthly_rolling_windows(dates: list[datetime], horizons: list[int]) -> list[tuple[int, int, int]]:
    windows: list[tuple[int, int, int]] = []
    seen_months: set[tuple[int, int]] = set()
    start_indices: list[int] = []
    for idx, dt in enumerate(dates):
        key = (dt.year, dt.month)
        if key not in seen_months:
            seen_months.add(key)
            start_indices.append(idx)

    for start_idx in start_indices:
        start_dt = dates[start_idx]
        for years in horizons:
            end_target = add_years(start_dt, years)
            end_idx = first_index_on_or_after(dates, end_target)
            if end_idx is not None and end_idx < len(dates):
                windows.append((years, start_idx, end_idx))
    return windows


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    qqq_map = read_prices(str(DATA_DIR / "synthetic-qqq.tsv"))
    tqqq_map = read_prices(str(DATA_DIR / "synthetic-tqqq.tsv"))
    rows = [
        (d, qqq_map[d], tqqq_map[d])
        for d in sorted(set(qqq_map) & set(tqqq_map))
        if d >= datetime(2010, 2, 11)
    ]
    dates = [r[0] for r in rows]
    qqq = [r[1] for r in rows]
    tqqq = [r[2] for r in rows]

    smas = [100, 125, 150, 175, 200, 225, 250]
    buffers = range(0, 9)
    setups = [(sma, buy, sell) for sma in smas for buy in buffers for sell in buffers]
    windows = monthly_rolling_windows(dates, [3, 5, 7, 10, 12])

    sma_cache = {sma: rolling_sma(qqq, sma) for sma in smas}
    equity_by_setup: dict[tuple[int, int, int], list[float]] = {}
    for setup in setups:
        sma, buy, sell = setup
        equity_by_setup[setup] = simulate_equity(qqq, tqqq, sma_cache[sma], buy, sell)

    cagr_by_setup: dict[tuple[int, int, int], list[float]] = {setup: [] for setup in setups}
    dd_by_setup: dict[tuple[int, int, int], list[float]] = {setup: [] for setup in setups}
    rank_pct_by_setup: dict[tuple[int, int, int], list[float]] = {setup: [] for setup in setups}
    top10_by_setup: dict[tuple[int, int, int], int] = {setup: 0 for setup in setups}
    top25_by_setup: dict[tuple[int, int, int], int] = {setup: 0 for setup in setups}
    beat_5_3_by_setup: dict[tuple[int, int, int], int] = {setup: 0 for setup in setups}

    baseline = (200, 5, 3)
    for years, start_idx, end_idx in windows:
        period_scores: list[tuple[float, tuple[int, int, int], float, float]] = []
        for setup in setups:
            equity = equity_by_setup[setup]
            final_x = equity[end_idx] / equity[start_idx]
            cagr = final_x ** (1 / years) - 1
            dd = max_drawdown_segment(equity, start_idx, end_idx)
            # Window-local score: return with a drawdown penalty.
            score = cagr + 0.20 * dd
            cagr_by_setup[setup].append(cagr)
            dd_by_setup[setup].append(dd)
            period_scores.append((score, setup, cagr, dd))

        period_scores.sort(reverse=True)
        baseline_cagr = next(cagr for _, setup, cagr, _ in period_scores if setup == baseline)
        denom = max(1, len(period_scores) - 1)
        top10_cutoff = max(1, int(len(period_scores) * 0.10))
        top25_cutoff = max(1, int(len(period_scores) * 0.25))
        for rank, (_, setup, cagr, _) in enumerate(period_scores):
            rank_pct = rank / denom
            rank_pct_by_setup[setup].append(rank_pct)
            if rank < top10_cutoff:
                top10_by_setup[setup] += 1
            if rank < top25_cutoff:
                top25_by_setup[setup] += 1
            if cagr > baseline_cagr:
                beat_5_3_by_setup[setup] += 1

    summary: list[SetupMetric] = []
    for setup in setups:
        cagr_values = cagr_by_setup[setup]
        dd_values = dd_by_setup[setup]
        rank_values = rank_pct_by_setup[setup]
        avg_rank = sum(rank_values) / len(rank_values)
        median_rank = percentile(rank_values, 0.5)
        avg_cagr = sum(cagr_values) / len(cagr_values)
        median_cagr = percentile(cagr_values, 0.5)
        p25_cagr = percentile(cagr_values, 0.25)
        avg_dd = sum(dd_values) / len(dd_values)
        worst_dd = min(dd_values)
        top10_rate = top10_by_setup[setup] / len(windows)
        top25_rate = top25_by_setup[setup] / len(windows)
        beat_rate = beat_5_3_by_setup[setup] / len(windows)
        # Lower rank is better; combine consistency and downside-aware returns.
        combined = (
            -avg_rank
            - 0.35 * median_rank
            + 0.25 * top10_rate
            + 0.10 * top25_rate
            + 0.35 * p25_cagr
            + 0.15 * median_cagr
            + 0.10 * avg_dd
        )
        summary.append(
            SetupMetric(
                sma=setup[0],
                buy=setup[1],
                sell=setup[2],
                avg_rank_pct=avg_rank,
                median_rank_pct=median_rank,
                top_10_rate=top10_rate,
                top_25_rate=top25_rate,
                avg_cagr=avg_cagr,
                median_cagr=median_cagr,
                p25_cagr=p25_cagr,
                avg_dd=avg_dd,
                worst_dd=worst_dd,
                beat_200_5_3_rate=beat_rate,
                score=combined,
            )
        )

    summary.sort(key=lambda r: r.score, reverse=True)

    print(f"Windows tested: {len(windows)} monthly rolling windows")
    print("Horizons: 3, 5, 7, 10, 12 years")
    print("Rank pct: 0% is best setup in a window; 100% is worst")
    print("\nTop robust setups")
    print("rank sma b/s avgRank medRank top10 top25 avgCAGR medCAGR p25CAGR avgDD worstDD beat5/3")
    for idx, row in enumerate(summary[:30], 1):
        print(
            f"{idx:>4} {row.sma:>3} {row.buy}/{row.sell:<2} "
            f"{row.avg_rank_pct:>7.1%} {row.median_rank_pct:>7.1%} "
            f"{row.top_10_rate:>5.1%} {row.top_25_rate:>5.1%} "
            f"{row.avg_cagr:>7.2%} {row.median_cagr:>7.2%} {row.p25_cagr:>7.2%} "
            f"{row.avg_dd:>7.2%} {row.worst_dd:>7.2%} {row.beat_200_5_3_rate:>7.1%}"
        )

    out_path = RESULTS_DIR / "significant_sma_sweep_summary.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([field for field in SetupMetric.__dataclass_fields__])
        for row in summary:
            writer.writerow([getattr(row, field) for field in SetupMetric.__dataclass_fields__])

    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
