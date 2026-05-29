from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"


@dataclass(frozen=True)
class WindowResult:
    window_id: int
    start: str
    end: str
    years: float
    sma: int
    buy: int
    sell: int
    cagr: float
    max_dd: float
    sharpe: float
    final_x: float
    trades: int


def read_prices(path: str) -> dict[datetime, float]:
    with Path(path).open(newline="") as f:
        return {
            datetime.strptime(row["Date"], "%m/%d/%Y %H:%M:%S"): float(row["Close"])
            for row in csv.DictReader(f, delimiter="\t")
        }


def max_drawdown(equity: list[float]) -> float:
    peak = equity[0]
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        worst = min(worst, value / peak - 1.0)
    return worst


def sharpe_ratio(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    avg = sum(returns) / len(returns)
    var = sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)
    sd = math.sqrt(var)
    return 0.0 if sd == 0 else avg / sd * math.sqrt(252)


def test_strategy(
    rows: list[tuple[datetime, float, float]],
    sma_len: int,
    buy_pct: int,
    sell_pct: int,
    cash_yield: float = 0.04,
) -> tuple[float, float, float, float, int]:
    dates = [r[0] for r in rows]
    qqq = [r[1] for r in rows]
    tqqq = [r[2] for r in rows]
    rolling_sma = [None] * len(rows)
    window_sum = 0.0
    for idx, price in enumerate(qqq):
        window_sum += price
        if idx >= sma_len:
            window_sum -= qqq[idx - sma_len]
        if idx >= sma_len - 1:
            rolling_sma[idx] = window_sum / sma_len
    invested = False
    equity = [1.0]
    returns: list[float] = []
    trades = 0
    cash_daily = cash_yield / 252.0

    for i in range(1, len(rows)):
        signal_idx = i - 1
        sma = rolling_sma[signal_idx]
        if sma is not None:
            close = qqq[signal_idx]
            if not invested and close > sma * (1 + buy_pct / 100):
                invested = True
                trades += 1
            elif invested and close < sma * (1 - sell_pct / 100):
                invested = False
                trades += 1

        day_return = tqqq[i] / tqqq[i - 1] - 1 if invested else cash_daily
        returns.append(day_return)
        equity.append(equity[-1] * (1 + day_return))

    years = (dates[-1] - dates[0]).days / 365.25
    cagr = equity[-1] ** (1 / years) - 1
    return cagr, max_drawdown(equity), sharpe_ratio(returns), equity[-1], trades


def make_windows(rows: list[tuple[datetime, float, float]]) -> list[list[tuple[datetime, float, float]]]:
    rng = random.Random(42)
    windows: list[list[tuple[datetime, float, float]]] = []
    trading_days_by_year = 252

    # Blend many economic regimes: short, medium, and long windows.
    lengths = (
        [3 * trading_days_by_year] * 4
        + [5 * trading_days_by_year] * 6
        + [7 * trading_days_by_year] * 5
        + [10 * trading_days_by_year] * 3
        + [12 * trading_days_by_year] * 2
    )
    for length in lengths:
        max_start = len(rows) - length - 1
        start_idx = rng.randint(0, max_start)
        windows.append(rows[start_idx : start_idx + length])
    return windows


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    idx = int(round((len(values) - 1) * p))
    return values[idx]


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    qqq = read_prices(str(DATA_DIR / "synthetic-qqq.tsv"))
    tqqq = read_prices(str(DATA_DIR / "synthetic-tqqq.tsv"))
    all_rows = [(d, qqq[d], tqqq[d]) for d in sorted(set(qqq) & set(tqqq))]
    real_rows = [r for r in all_rows if r[0] >= datetime(2010, 2, 11)]
    windows = make_windows(real_rows)

    smas = [100, 125, 150, 175, 200, 225, 250]
    buffers = range(0, 9)
    results: list[WindowResult] = []

    for window_id, window in enumerate(windows, 1):
        years = (window[-1][0] - window[0][0]).days / 365.25
        for sma in smas:
            if len(window) <= sma + 10:
                continue
            for buy in buffers:
                for sell in buffers:
                    cagr, dd, sharpe, final_x, trades = test_strategy(window, sma, buy, sell)
                    results.append(
                        WindowResult(
                            window_id=window_id,
                            start=window[0][0].date().isoformat(),
                            end=window[-1][0].date().isoformat(),
                            years=years,
                            sma=sma,
                            buy=buy,
                            sell=sell,
                            cagr=cagr,
                            max_dd=dd,
                            sharpe=sharpe,
                            final_x=final_x,
                            trades=trades,
                        )
                    )

    grouped: dict[tuple[int, int, int], list[WindowResult]] = {}
    for result in results:
        grouped.setdefault((result.sma, result.buy, result.sell), []).append(result)

    summary = []
    for key, rows in grouped.items():
        cagr_values = [r.cagr for r in rows]
        sharpe_values = [r.sharpe for r in rows]
        dd_values = [r.max_dd for r in rows]
        avg_cagr = sum(cagr_values) / len(cagr_values)
        median_cagr = percentile(cagr_values, 0.5)
        p25_cagr = percentile(cagr_values, 0.25)
        win_rate = sum(1 for r in rows if r.cagr > 0.30) / len(rows)
        avg_sharpe = sum(sharpe_values) / len(sharpe_values)
        worst_dd = min(dd_values)
        avg_dd = sum(dd_values) / len(dd_values)
        # Rewards returns that persist across windows; penalizes fragile drawdown.
        score = p25_cagr + 0.35 * median_cagr + 0.08 * avg_sharpe + 0.12 * avg_dd + 0.10 * worst_dd
        summary.append((score, avg_cagr, median_cagr, p25_cagr, win_rate, avg_sharpe, avg_dd, worst_dd, key))

    summary.sort(reverse=True)

    print("20-window robust ranking, real TQQQ era only")
    print("rank sma b/s score avgCAGR medCAGR p25CAGR win>30 avgSharpe avgDD worstDD")
    for rank, row in enumerate(summary[:30], 1):
        score, avg_cagr, median_cagr, p25_cagr, win_rate, avg_sharpe, avg_dd, worst_dd, key = row
        sma, buy, sell = key
        print(
            f"{rank:>4} {sma:>3} {buy}/{sell:<2} {score:>6.3f} "
            f"{avg_cagr:>7.2%} {median_cagr:>7.2%} {p25_cagr:>7.2%} "
            f"{win_rate:>6.1%} {avg_sharpe:>8.2f} {avg_dd:>7.2%} {worst_dd:>7.2%}"
        )

    summary_path = RESULTS_DIR / "hundred_window_sweep_summary.csv"
    with summary_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "sma",
                "buy",
                "sell",
                "score",
                "avg_cagr",
                "median_cagr",
                "p25_cagr",
                "win_rate_cagr_gt_30",
                "avg_sharpe",
                "avg_dd",
                "worst_dd",
            ]
        )
        for row in summary:
            score, avg_cagr, median_cagr, p25_cagr, win_rate, avg_sharpe, avg_dd, worst_dd, key = row
            writer.writerow([*key, score, avg_cagr, median_cagr, p25_cagr, win_rate, avg_sharpe, avg_dd, worst_dd])

    results_path = RESULTS_DIR / "hundred_window_sweep_results.csv"
    with results_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([field for field in WindowResult.__dataclass_fields__])
        for result in results:
            writer.writerow([getattr(result, field) for field in WindowResult.__dataclass_fields__])

    print(f"\nWrote {summary_path} and {results_path}")


if __name__ == "__main__":
    main()
