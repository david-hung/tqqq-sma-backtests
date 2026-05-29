from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
QQQ_FILE = DATA_DIR / "synthetic-qqq.tsv"
TQQQ_FILE = DATA_DIR / "synthetic-tqqq.tsv"


@dataclass(frozen=True)
class Result:
    period: str
    sma: int
    buy_buffer: int
    sell_buffer: int
    cagr: float
    max_drawdown: float
    calmar: float
    sharpe: float
    trades: int
    exposure: float
    final_value: float


def read_prices(path: Path) -> dict[datetime, float]:
    prices: dict[datetime, float] = {}
    with path.open(newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            dt = datetime.strptime(row["Date"], "%m/%d/%Y %H:%M:%S")
            prices[dt] = float(row["Close"])
    return prices


def max_drawdown(equity: list[float]) -> float:
    peak = equity[0]
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        worst = min(worst, value / peak - 1.0)
    return worst


def annualized_return(start_value: float, end_value: float, years: float) -> float:
    return (end_value / start_value) ** (1.0 / years) - 1.0


def sharpe_ratio(daily_returns: list[float]) -> float:
    if len(daily_returns) < 2:
        return 0.0
    avg = sum(daily_returns) / len(daily_returns)
    var = sum((r - avg) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    sd = math.sqrt(var)
    return 0.0 if sd == 0 else avg / sd * math.sqrt(252)


def run_strategy(
    dates: list[datetime],
    qqq: list[float],
    tqqq: list[float],
    sma_len: int,
    buy_buffer_pct: int,
    sell_buffer_pct: int,
    cash_yield: float = 0.04,
) -> tuple[float, float, float, int, float, float]:
    invested = False
    trades = 0
    equity = [1.0]
    daily_returns: list[float] = []
    invested_days = 0
    cash_daily = cash_yield / 252.0

    for i in range(1, len(dates)):
        signal_idx = i - 1
        if signal_idx >= sma_len - 1:
            sma = sum(qqq[signal_idx - sma_len + 1 : signal_idx + 1]) / sma_len
            close = qqq[signal_idx]
            if not invested and close > sma * (1.0 + buy_buffer_pct / 100.0):
                invested = True
                trades += 1
            elif invested and close < sma * (1.0 - sell_buffer_pct / 100.0):
                invested = False
                trades += 1

        if invested:
            day_return = tqqq[i] / tqqq[i - 1] - 1.0
            invested_days += 1
        else:
            day_return = cash_daily

        daily_returns.append(day_return)
        equity.append(equity[-1] * (1.0 + day_return))

    years = (dates[-1] - dates[0]).days / 365.25
    cagr = annualized_return(1.0, equity[-1], years)
    dd = max_drawdown(equity)
    calmar = cagr / abs(dd) if dd < 0 else 0.0
    sharpe = sharpe_ratio(daily_returns)
    exposure = invested_days / max(1, len(dates) - 1)
    return cagr, dd, calmar, trades, exposure, equity[-1], sharpe


def run_strategy_dca(
    dates: list[datetime],
    qqq: list[float],
    tqqq: list[float],
    sma_len: int,
    buy_buffer_pct: int,
    sell_buffer_pct: int,
    cash_yield: float = 0.04,
    initial: float = 1000.0,
    monthly: float = 100.0,
) -> tuple[float, float, float, int, float, float]:
    invested = False
    trades = 0
    equity = [initial]
    daily_returns: list[float] = []
    invested_days = 0
    cash_daily = cash_yield / 252.0
    last_contribution_month = (dates[0].year, dates[0].month)

    for i in range(1, len(dates)):
        current_month = (dates[i].year, dates[i].month)
        if current_month != last_contribution_month:
            equity[-1] += monthly
            last_contribution_month = current_month

        signal_idx = i - 1
        if signal_idx >= sma_len - 1:
            sma = sum(qqq[signal_idx - sma_len + 1 : signal_idx + 1]) / sma_len
            close = qqq[signal_idx]
            if not invested and close > sma * (1.0 + buy_buffer_pct / 100.0):
                invested = True
                trades += 1
            elif invested and close < sma * (1.0 - sell_buffer_pct / 100.0):
                invested = False
                trades += 1

        if invested:
            day_return = tqqq[i] / tqqq[i - 1] - 1.0
            invested_days += 1
        else:
            day_return = cash_daily

        daily_returns.append(day_return)
        equity.append(equity[-1] * (1.0 + day_return))

    dd = max_drawdown(equity)
    total_contrib = initial + monthly * (
        (dates[-1].year - dates[0].year) * 12 + dates[-1].month - dates[0].month
    )
    gain_multiple = equity[-1] / total_contrib
    sharpe = sharpe_ratio(daily_returns)
    exposure = invested_days / max(1, len(dates) - 1)
    return gain_multiple, dd, 0.0, trades, exposure, equity[-1], sharpe


def slice_period(
    merged: list[tuple[datetime, float, float]], start: str
) -> tuple[list[datetime], list[float], list[float]]:
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    rows = [row for row in merged if row[0] >= start_dt]
    return [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]


def sweep(period: str, dates: list[datetime], qqq: list[float], tqqq: list[float]) -> list[Result]:
    results: list[Result] = []
    for sma in [100, 125, 150, 175, 200, 225, 250]:
        for buy in range(0, 9):
            for sell in range(0, 9):
                cagr, dd, calmar, trades, exposure, final_value, sharpe = run_strategy(
                    dates, qqq, tqqq, sma, buy, sell
                )
                results.append(
                    Result(
                        period=period,
                        sma=sma,
                        buy_buffer=buy,
                        sell_buffer=sell,
                        cagr=cagr,
                        max_drawdown=dd,
                        calmar=calmar,
                        sharpe=sharpe,
                        trades=trades,
                        exposure=exposure,
                        final_value=final_value,
                    )
                )
    return results


def print_table(title: str, rows: list[Result], limit: int = 12) -> None:
    print(f"\n{title}")
    print("rank  sma  buy/sell  CAGR     MaxDD    Calmar  Sharpe  Trades  Exposure  Final")
    for rank, r in enumerate(rows[:limit], 1):
        print(
            f"{rank:>4}  {r.sma:>3}  {r.buy_buffer:>2}/{r.sell_buffer:<2}    "
            f"{r.cagr:>7.2%}  {r.max_drawdown:>7.2%}  {r.calmar:>6.2f}  "
            f"{r.sharpe:>6.2f}  {r.trades:>6}  {r.exposure:>8.1%}  {r.final_value:>8.1f}x"
        )


def print_dca_table(
    title: str,
    rows: list[tuple[int, int, int, float, float, int, float, float, float]],
    limit: int = 12,
) -> None:
    print(f"\n{title}")
    print("rank  sma  buy/sell  wealth/contrib  MaxDD    Sharpe  Trades  Exposure  Final")
    for rank, (sma, buy, sell, multiple, dd, trades, exposure, final_value, sharpe) in enumerate(
        rows[:limit], 1
    ):
        print(
            f"{rank:>4}  {sma:>3}  {buy:>2}/{sell:<2}    "
            f"{multiple:>8.2f}x      {dd:>7.2%}  {sharpe:>6.2f}  "
            f"{trades:>6}  {exposure:>8.1%}  ${final_value:,.0f}"
        )


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    qqq_prices = read_prices(QQQ_FILE)
    tqqq_prices = read_prices(TQQQ_FILE)
    common_dates = sorted(set(qqq_prices) & set(tqqq_prices))
    merged = [(dt, qqq_prices[dt], tqqq_prices[dt]) for dt in common_dates]

    periods = {
        "real_tqqq_2010": "2010-02-11",
        "qqq_real_1999_synth_tqqq": "1999-03-10",
    }

    all_results: list[Result] = []
    for period, start in periods.items():
        dates, qqq, tqqq = slice_period(merged, start)
        results = sweep(period, dates, qqq, tqqq)
        all_results.extend(results)

        print(f"\n=== {period}: {dates[0].date()} to {dates[-1].date()} ===")
        print_table("Top by CAGR", sorted(results, key=lambda r: r.cagr, reverse=True))
        print_table("Top by Calmar (CAGR / max drawdown)", sorted(results, key=lambda r: r.calmar, reverse=True))
        sane = [r for r in results if r.max_drawdown >= -0.60]
        print_table("Top CAGR with max drawdown no worse than -60%", sorted(sane, key=lambda r: r.cagr, reverse=True))

        if period == "real_tqqq_2010":
            dca_rows = []
            for sma in [100, 125, 150, 175, 200, 225, 250]:
                for buy in range(0, 9):
                    for sell in range(0, 9):
                        multiple, dd, _, trades, exposure, final_value, sharpe = run_strategy_dca(
                            dates, qqq, tqqq, sma, buy, sell
                        )
                        dca_rows.append((sma, buy, sell, multiple, dd, trades, exposure, final_value, sharpe))
            print_dca_table(
                "DCA test, $1,000 initial + $100/month, top by final wealth / contributions",
                sorted(dca_rows, key=lambda r: r[3], reverse=True),
            )

    out = RESULTS_DIR / "sma_buffer_sweep_results.csv"
    with out.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([field for field in Result.__dataclass_fields__])
        for r in all_results:
            writer.writerow(
                [
                    r.period,
                    r.sma,
                    r.buy_buffer,
                    r.sell_buffer,
                    r.cagr,
                    r.max_drawdown,
                    r.calmar,
                    r.sharpe,
                    r.trades,
                    r.exposure,
                    r.final_value,
                ]
            )
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
