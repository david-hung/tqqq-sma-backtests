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
class Row:
    period: str
    start: str
    end: str
    sma: int
    buy: int
    sell: int
    cagr: float
    max_dd: float
    sharpe: float
    trades: int
    final_x: float


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
) -> tuple[float, float, float, int, float]:
    dates = [r[0] for r in rows]
    qqq = [r[1] for r in rows]
    tqqq = [r[2] for r in rows]
    invested = False
    equity = [1.0]
    returns: list[float] = []
    trades = 0
    cash_daily = cash_yield / 252.0

    for i in range(1, len(rows)):
        signal_idx = i - 1
        if signal_idx >= sma_len - 1:
            sma = sum(qqq[signal_idx - sma_len + 1 : signal_idx + 1]) / sma_len
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
    return cagr, max_drawdown(equity), sharpe_ratio(returns), trades, equity[-1]


def slice_rows(
    rows: list[tuple[datetime, float, float]], start: str, end: str | None = None
) -> list[tuple[datetime, float, float]]:
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d") if end else datetime.max
    return [r for r in rows if start_dt <= r[0] <= end_dt]


def sweep_period(
    period: str,
    rows: list[tuple[datetime, float, float]],
    smas: list[int],
    buffers: range,
) -> list[Row]:
    out: list[Row] = []
    for sma in smas:
        if len(rows) <= sma + 10:
            continue
        for buy in buffers:
            for sell in buffers:
                cagr, dd, sharpe, trades, final_x = test_strategy(rows, sma, buy, sell)
                out.append(
                    Row(
                        period=period,
                        start=rows[0][0].date().isoformat(),
                        end=rows[-1][0].date().isoformat(),
                        sma=sma,
                        buy=buy,
                        sell=sell,
                        cagr=cagr,
                        max_dd=dd,
                        sharpe=sharpe,
                        trades=trades,
                        final_x=final_x,
                    )
                )
    return out


def print_top(title: str, rows: list[Row], key: str, limit: int = 10) -> None:
    sorted_rows = sorted(rows, key=lambda r: getattr(r, key), reverse=True)
    print(f"\n{title}")
    print("rank period       sma b/s  CAGR    DD      Sharpe trades final")
    for rank, r in enumerate(sorted_rows[:limit], 1):
        print(
            f"{rank:>4} {r.period:<12} {r.sma:>3} {r.buy}/{r.sell:<2} "
            f"{r.cagr:>7.2%} {r.max_dd:>7.2%} {r.sharpe:>6.2f} {r.trades:>5} {r.final_x:>7.1f}x"
        )


def summarize_robust(all_rows: list[Row], periods: list[str]) -> None:
    grouped: dict[tuple[int, int, int], list[Row]] = {}
    for row in all_rows:
        if row.period in periods:
            grouped.setdefault((row.sma, row.buy, row.sell), []).append(row)

    summary = []
    for key, rows in grouped.items():
        if len(rows) != len(periods):
            continue
        avg_cagr = sum(r.cagr for r in rows) / len(rows)
        min_cagr = min(r.cagr for r in rows)
        worst_dd = min(r.max_dd for r in rows)
        avg_sharpe = sum(r.sharpe for r in rows) / len(rows)
        avg_rank_score = avg_cagr + 0.08 * avg_sharpe + 0.25 * worst_dd
        summary.append((avg_rank_score, avg_cagr, min_cagr, worst_dd, avg_sharpe, key))

    summary.sort(reverse=True)
    print("\nRobust ranking across selected periods")
    print("rank sma b/s  score  avgCAGR minCAGR worstDD avgSharpe")
    for rank, (score, avg_cagr, min_cagr, worst_dd, avg_sharpe, key) in enumerate(summary[:20], 1):
        sma, buy, sell = key
        print(
            f"{rank:>4} {sma:>3} {buy}/{sell:<2} {score:>6.3f} "
            f"{avg_cagr:>7.2%} {min_cagr:>7.2%} {worst_dd:>7.2%} {avg_sharpe:>8.2f}"
        )


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    qqq = read_prices(str(DATA_DIR / "synthetic-qqq.tsv"))
    tqqq = read_prices(str(DATA_DIR / "synthetic-tqqq.tsv"))
    merged = [(d, qqq[d], tqqq[d]) for d in sorted(set(qqq) & set(tqqq))]

    periods = {
        "2010-full": ("2010-02-11", None),
        "2013-site": ("2013-09-30", None),
        "2015-start": ("2015-01-02", None),
        "2018-start": ("2018-01-02", None),
        "2020-start": ("2020-01-02", None),
        "2022-start": ("2022-01-03", None),
        "2010-2015": ("2010-02-11", "2015-12-31"),
        "2016-2020": ("2016-01-04", "2020-12-31"),
        "2021-2026": ("2021-01-04", None),
    }
    smas = [100, 125, 150, 175, 200, 225, 250]
    all_rows: list[Row] = []
    for period, (start, end) in periods.items():
        rows = slice_rows(merged, start, end)
        results = sweep_period(period, rows, smas, range(0, 9))
        all_rows.extend(results)
        print_top(f"Top CAGR for {period}", results, "cagr", limit=8)
        print_top(f"Top Sharpe for {period}", results, "sharpe", limit=5)

    summarize_robust(
        all_rows,
        ["2010-full", "2013-site", "2015-start", "2018-start", "2020-start", "2016-2020", "2021-2026"],
    )

    out_path = RESULTS_DIR / "robust_sma_sweep_results.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([field for field in Row.__dataclass_fields__])
        for row in all_rows:
            writer.writerow([getattr(row, field) for field in Row.__dataclass_fields__])
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
