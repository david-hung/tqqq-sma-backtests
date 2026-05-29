from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def read(path: str) -> dict[datetime, float]:
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


def run(mode: str) -> None:
    qqq_map = read(str(DATA_DIR / "synthetic-qqq.tsv"))
    tqqq_map = read(str(DATA_DIR / "synthetic-tqqq.tsv"))
    dates = [d for d in sorted(set(qqq_map) & set(tqqq_map)) if d >= datetime(2010, 4, 1)]
    qqq = [qqq_map[d] for d in dates]
    tqqq = [tqqq_map[d] for d in dates]
    equity = [10_000.0]
    invested = False
    last_quarter = (dates[0].year, (dates[0].month - 1) // 3)
    trades = 0

    for i in range(1, len(dates)):
        quarter = (dates[i].year, (dates[i].month - 1) // 3)
        if quarter != last_quarter:
            equity[-1] += 400.0
            last_quarter = quarter

        daily_return = tqqq[i] / tqqq[i - 1] - 1 if invested else 0.04 / 252

        signal_idx = i if mode == "lookahead" else i - 1
        if signal_idx >= 199:
            sma = sum(qqq[signal_idx - 199 : signal_idx + 1]) / 200
            close = qqq[signal_idx]
            if not invested and close > sma:
                invested = True
                trades += 1
                if mode == "lookahead":
                    daily_return = tqqq[i] / tqqq[i - 1] - 1
            elif invested and close < sma * 0.95:
                invested = False
                trades += 1
                if mode == "lookahead":
                    daily_return = 0.04 / 252

        equity.append(equity[-1] * (1 + daily_return))

    print(mode, f"${equity[-1]:,.0f}", f"dd={max_dd(equity):.1%}", f"trades={trades}")


run("next-day")
run("lookahead")
