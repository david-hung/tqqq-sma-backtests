# TQQQ SMA Buffer Backtests

This folder contains the scripts and data used to compare QQQ SMA buffer rules for trading TQQQ.

The goal is to find parameters that are robust across many possible start/end dates, not just the single best historical backtest.

## Data

- `data/synthetic-qqq.tsv`
- `data/synthetic-tqqq.tsv`

These files were downloaded from 9Sig/Networthcast public data.

## Files

- `significant_sma_sweep.py` - main robustness test. Uses monthly rolling windows across 3, 5, 7, 10, and 12 year horizons, ranks every setup inside each window, then aggregates robustness.
- `data/` - source QQQ and TQQQ data.
- `results/significant_sma_sweep_summary.csv` - final ranked results from the main sweep.

## Current Finding

The most robust tested setup was:

```text
Trade: TQQQ
Signal: QQQ
SMA: 175 days
Buy buffer: 0%
Sell buffer: 2%
Cash yield while out: 4%
Execution: next day after signal
```

The full summary is in `results/significant_sma_sweep_summary.csv`.

## Run

Run from the repo root:

```powershell
python significant_sma_sweep.py
```

The script rewrites `results/significant_sma_sweep_summary.csv`.

## Tested Parameter Grid

```text
SMA lengths: 100, 125, 150, 175, 200, 225, 250
Buy buffers: 0% through 8%
Sell buffers: 0% through 8%
Total setups: 567
```

## Main Robustness Method

`significant_sma_sweep.py` tests each setup across monthly rolling windows:

```text
Data period: 2010-02-11 to 2026-05-28
Window lengths: 3, 5, 7, 10, and 12 years
Total rolling windows: 536
Execution: next-day after signal
Cash yield: 4% annualized
```

Each setup is ranked within each exact same window, then the ranks are aggregated. This avoids treating one arbitrary timeframe as the answer.

## Top Results

| Rank | SMA | Buy | Sell | Avg Rank | Top 10% Rate | Avg CAGR | 25th %ile CAGR | Avg Drawdown |
| ---: | --: | --: | ---: | -------: | -----------: | -------: | -------------: | -----------: |
| 1 | 175 | 0% | 2% | 9.0% | 72.2% | 42.29% | 34.51% | -49.39% |
| 2 | 150 | 0% | 0% | 9.8% | 70.0% | 41.23% | 35.39% | -47.78% |
| 3 | 150 | 1% | 3% | 10.1% | 66.2% | 41.03% | 33.93% | -49.38% |
| 4 | 175 | 0% | 3% | 10.3% | 64.7% | 40.78% | 34.22% | -49.51% |
| 5 | 150 | 0% | 1% | 11.1% | 55.6% | 40.21% | 34.37% | -48.29% |
| 6 | 175 | 1% | 3% | 11.9% | 52.6% | 40.12% | 33.37% | -49.12% |
| 7 | 175 | 7% | 2% | 13.2% | 56.0% | 38.88% | 33.52% | -46.16% |
| 8 | 175 | 2% | 3% | 13.5% | 56.3% | 40.09% | 32.25% | -48.66% |
| 9 | 150 | 7% | 3% | 13.8% | 52.8% | 38.11% | 33.49% | -43.45% |
| 10 | 175 | 1% | 2% | 12.8% | 49.1% | 40.54% | 32.82% | -49.22% |

## Baseline

A simple buy-and-hold TQQQ baseline was tested across the same 536 rolling windows used for the SMA strategies:

```text
Data period: 2010-02-11 to 2026-05-28
Window lengths: 3, 5, 7, 10, and 12 years
Total rolling windows: 536

Buy-and-hold TQQQ average CAGR: 41.34%
Buy-and-hold TQQQ median CAGR: 40.99%
Buy-and-hold TQQQ 25th percentile CAGR: 33.58%
Buy-and-hold TQQQ average drawdown: -66.09%
Buy-and-hold TQQQ worst drawdown: -81.66%
```

The leading SMA setup, `175 SMA, 0/2`, had a similar average CAGR across the rolling windows but materially lower drawdowns:

```text
175 SMA, 0/2 average CAGR: 42.29%
175 SMA, 0/2 25th percentile CAGR: 34.51%
175 SMA, 0/2 average drawdown: -49.39%
175 SMA, 0/2 worst drawdown: -55.35%
```

The SMA strategy is not trying to maximize one cherry-picked full-period CAGR. It is trying to find rules that hold up across many possible entry and exit windows while reducing drawdown exposure compared with simply holding TQQQ through every crash.

## Conclusion

The most robust setup in this test was `175 SMA, 0/2`: buy TQQQ when QQQ closes above its 175-day SMA, and sell when QQQ closes 2% below that SMA. It had the best overall rank across 536 rolling windows and stayed in the top 10% of all tested setups in 72.2% of windows.

The results suggest that the best general range is:

```text
SMA length: 150 to 175 days
Buy buffer: 0% to 1%
Sell buffer: 0% to 3%
```

The commonly used 200-day SMA is still defensible because it is simple, widely watched, and less likely to look overfit. However, in this test it appeared somewhat slow for TQQQ. The 150-175 day range captured rebounds earlier while still filtering major downtrends.

For a practical default, this research favors:

```text
Primary choice: 175 SMA, 0/2
Simpler aggressive alternative: 150 SMA, 0/0
More conventional alternative: 200 SMA with small or no buffers
```

These results should be treated as backtest research, not a guarantee. TQQQ is a daily-reset leveraged ETF, and future market structure, volatility, rates, taxes, slippage, and execution timing can materially change real-world results.
