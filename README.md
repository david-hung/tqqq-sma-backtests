# TQQQ SMA Buffer Backtests

This folder contains the scripts and data used to compare QQQ SMA buffer rules for trading TQQQ.

The goal is to find parameters that are robust across many possible start/end dates, not just the single best historical backtest.

## Data

- `data/synthetic-qqq.tsv`
- `data/synthetic-tqqq.tsv`

These files were downloaded from 9Sig/Networthcast public data.

## Main Scripts

- `significant_sma_sweep.py` - strongest methodology so far. Uses monthly rolling windows across 3, 5, 7, 10, and 12 year horizons, ranks every setup inside each window, then aggregates robustness.
- `hundred_window_sweep.py` - randomized window robustness test.
- `robust_sma_sweep.py` - fixed-period comparison.
- `sma_buffer_sweep.py` - broad basic sweep.
- `compare_9sig_period.py` and `match_9sig_check.py` - checks used to compare against the 9Sig site screenshots.

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
