# TQQQ SMA Buffer Backtests

This repo tests whether a simple moving average filter on QQQ can improve a TQQQ strategy versus simply holding TQQQ.

The short version: **the SMA filter did not show a large CAGR advantage over buy-and-hold TQQQ.** The stronger result was drawdown reduction. The best tested SMA setup had roughly similar average CAGR to buy-and-hold, but much lower average and worst drawdowns across rolling timeframes.

This is backtest research, not financial advice.

## Strategy

The tested strategy uses QQQ as the signal and TQQQ as the traded asset.

```text
Trade asset: TQQQ
Signal asset: QQQ
Risk-off asset: cash
Cash yield while out: 4% annualized
Execution: next trading day after the signal
```

The SMA rule:

```text
Buy TQQQ when QQQ closes above SMA * (1 + buy_buffer)
Sell TQQQ when QQQ closes below SMA * (1 - sell_buffer)
```

Example:

```text
175 SMA, 0/2
= buy when QQQ closes above its 175-day SMA
= sell when QQQ closes 2% below its 175-day SMA
```

## What Was Tested

The sweep tested 567 SMA/buffer combinations.

```text
SMA lengths: 100, 125, 150, 175, 200, 225, 250
Buy buffers: 0% through 8%
Sell buffers: 0% through 8%
```

Data:

```text
Period: 2010-02-11 to 2026-05-28
Source files: data/synthetic-qqq.tsv and data/synthetic-tqqq.tsv
```

## Method

The main script is `significant_sma_sweep.py`.

Instead of judging one start date, each setup was tested across monthly rolling windows:

```text
Window lengths: 3, 5, 7, 10, and 12 years
Total rolling windows: 536
```

Within each rolling window, all 567 setups were tested on the exact same dates and ranked against each other. The final ranking favors setups that repeatedly rank near the top across many windows.

Important: this is **not** a formal statistical significance test. The results are best interpreted as a robustness comparison.

## Main Results

| Rank | Setup | SMA | Buy | Sell | Avg Rank | Top 10% Rate | Avg CAGR | 25th %ile CAGR | Avg Drawdown |
| ---: | ----- | --: | --: | ---: | -------: | -----------: | -------: | -------------: | -----------: |
| Baseline | Buy & Hold TQQQ | N/A | N/A | N/A | N/A | N/A | 41.34% | 33.58% | -66.09% |
| 1 | SMA Strategy | 175 | 0% | 2% | 9.0% | 72.2% | 42.29% | 34.51% | -49.39% |
| 2 | SMA Strategy | 150 | 0% | 0% | 9.8% | 70.0% | 41.23% | 35.39% | -47.78% |
| 3 | SMA Strategy | 150 | 1% | 3% | 10.1% | 66.2% | 41.03% | 33.93% | -49.38% |
| 4 | SMA Strategy | 175 | 0% | 3% | 10.3% | 64.7% | 40.78% | 34.22% | -49.51% |
| 5 | SMA Strategy | 150 | 0% | 1% | 11.1% | 55.6% | 40.21% | 34.37% | -48.29% |
| 6 | SMA Strategy | 175 | 1% | 3% | 11.9% | 52.6% | 40.12% | 33.37% | -49.12% |
| 7 | SMA Strategy | 175 | 7% | 2% | 13.2% | 56.0% | 38.88% | 33.52% | -46.16% |
| 8 | SMA Strategy | 175 | 2% | 3% | 13.5% | 56.3% | 40.09% | 32.25% | -48.66% |
| 9 | SMA Strategy | 150 | 7% | 3% | 13.8% | 52.8% | 38.11% | 33.49% | -43.45% |
| 10 | SMA Strategy | 175 | 1% | 2% | 12.8% | 49.1% | 40.54% | 32.82% | -49.22% |

`Avg Rank` means the average percentile rank across the rolling windows. Lower is better. An average rank of `9.0%` means the setup was usually near the top 9% of all tested parameter combinations.

## Interpretation

The best ranked setup was:

```text
175 SMA, 0/2
```

But its CAGR was only slightly higher than buy-and-hold:

```text
Buy-and-hold average CAGR: 41.34%
175 SMA, 0/2 average CAGR: 42.29%
Difference: +0.95 percentage points
```

That CAGR difference is small. I would not treat it as strong evidence that the SMA rule meaningfully outperforms buy-and-hold on returns.

The drawdown difference is much larger:

```text
Buy-and-hold average drawdown: -66.09%
175 SMA, 0/2 average drawdown: -49.39%

Buy-and-hold worst drawdown: -81.66%
175 SMA, 0/2 worst drawdown: -55.35%
```

So the best summary is:

```text
The SMA strategy produced similar average CAGR to buy-and-hold,
but with materially lower drawdowns in this backtest.
```

## Practical Takeaway

This test does **not** prove that SMA timing is a magic return enhancer. The evidence is more modest:

```text
SMA timing may improve the risk profile of TQQQ.
It may not significantly improve CAGR versus buy-and-hold.
```

The most robust parameter area was:

```text
SMA length: 150 to 175 days
Buy buffer: 0% to 1%
Sell buffer: 0% to 3%
```

The commonly used 200-day SMA is still reasonable. It is simple, widely followed, and less likely to look overfit. In this test, though, the 150-175 day range ranked better, likely because TQQQ benefits from catching rebounds earlier.

## Files

- `significant_sma_sweep.py` - main rolling-window parameter sweep.
- `data/` - source QQQ/TQQQ data files.
- `results/significant_sma_sweep_summary.csv` - ranked output from the sweep.

Run:

```powershell
python significant_sma_sweep.py
```

## Caveats

- TQQQ is a daily-reset 3x leveraged ETF.
- Backtests do not include taxes, trading costs, spreads, behavioral mistakes, or real-world execution friction.
- The sample only covers real TQQQ history from 2010 through 2026.
- Parameter sweeps can overfit, even when rolling windows are used.
- Future volatility, rates, and market structure may differ from the tested period.
