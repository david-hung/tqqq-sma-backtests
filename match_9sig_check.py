from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def read(path: str) -> list[tuple[datetime, float]]:
    rows = []
    with Path(path).open(newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rows.append((datetime.strptime(row["Date"], "%m/%d/%Y %H:%M:%S"), float(row["Close"])))
    return rows


def main() -> None:
    tqqq = [(d, p) for d, p in read(str(DATA_DIR / "synthetic-tqqq.tsv")) if d >= datetime(2010, 4, 1)]
    shares = 10000 / tqqq[0][1]
    last_q = (tqqq[0][0].year, (tqqq[0][0].month - 1) // 3)
    for d, p in tqqq[1:]:
        q = (d.year, (d.month - 1) // 3)
        if q != last_q:
            shares += 400 / p
            last_q = q
    value = shares * tqqq[-1][1]
    print(tqqq[0], tqqq[-1], value)

    shares = 10000 / tqqq[0][1]
    for d, p in tqqq[1:]:
        if d.month == 1 and d.day < 8:
            pass


if __name__ == "__main__":
    main()
