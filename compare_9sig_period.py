from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def read_prices(path: str) -> dict[datetime, float]:
    with Path(path).open(newline="") as f:
        return {
            datetime.strptime(row["Date"], "%m/%d/%Y %H:%M:%S"): float(row["Close"])
            for row in csv.DictReader(f, delimiter="\t")
        }


def max_dd(values: list[float]) -> float:
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        worst = min(worst, value / peak - 1.0)
    return worst


def test(start_date: str, mode: str) -> None:
    qqq_map = read_prices(str(DATA_DIR / "synthetic-qqq.tsv"))
    tqqq_map = read_prices(str(DATA_DIR / "synthetic-tqqq.tsv"))
    dates = [d for d in sorted(set(qqq_map) & set(tqqq_map)) if d >= datetime.strptime(start_date, "%Y-%m-%d")]
    qqq = [qqq_map[d] for d in dates]
    tqqq = [tqqq_map[d] for d in dates]

    equity = [10_000.0]
    invested = False
    trades = 0
    for i in range(1, len(dates)):
        daily_return = tqqq[i] / tqqq[i - 1] - 1 if invested else 0.04 / 252

        if mode == "pre-close-lookahead":
            signal_idx = i
            if signal_idx >= 199:
                sma = sum(qqq[signal_idx - 199 : signal_idx + 1]) / 200
                close = qqq[signal_idx]
                if not invested and close > sma:
                    invested = True
                    trades += 1
                    daily_return = tqqq[i] / tqqq[i - 1] - 1
                elif invested and close < sma * 0.95:
                    invested = False
                    trades += 1
                    daily_return = 0.04 / 252

        if mode == "buy-lookahead-sell-close":
            signal_idx = i
            if signal_idx >= 199:
                sma = sum(qqq[signal_idx - 199 : signal_idx + 1]) / 200
                close = qqq[signal_idx]
                if not invested and close > sma:
                    invested = True
                    trades += 1
                    daily_return = tqqq[i] / tqqq[i - 1] - 1
                elif invested and close < sma * 0.95:
                    trades += 1
                    invested = False

        if mode == "next-day":
            signal_idx = i - 1
            if signal_idx >= 199:
                sma = sum(qqq[signal_idx - 199 : signal_idx + 1]) / 200
                close = qqq[signal_idx]
                if not invested and close > sma:
                    invested = True
                    trades += 1
                elif invested and close < sma * 0.95:
                    invested = False
                    trades += 1

        equity.append(equity[-1] * (1 + daily_return))

    years = (dates[-1] - dates[0]).days / 365.25
    cagr = (equity[-1] / equity[0]) ** (1 / years) - 1
    print(
        start_date,
        mode,
        dates[0].date(),
        dates[-1].date(),
        f"final=${equity[-1]:,.0f}",
        f"cagr={cagr:.1%}",
        f"dd={max_dd(equity):.1%}",
        f"trades={trades}",
    )


for start in ["2013-09-30", "2013-10-01", "2013-09-23", "2013-09-01"]:
    test(start, "next-day")
    test(start, "pre-close-lookahead")
    test(start, "buy-lookahead-sell-close")
