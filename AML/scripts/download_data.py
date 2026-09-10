"""Download the PaySim dataset from a public mirror and verify its integrity.

Mirror: HuggingFace dataset `theman10/paysim` (raw CSV of Kaggle ealaxi/paysim1).
Hard-fails if the row count or fraud count does not match the published dataset.
"""

import sys
import time
import urllib.request
from pathlib import Path

URL = "https://huggingface.co/datasets/theman10/paysim/resolve/main/paysim.csv"
EXPECTED_BYTES = 493_534_783
EXPECTED_ROWS = 6_362_620
EXPECTED_FRAUDS = 8_213

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
CSV_PATH = DATA_DIR / "paysim.csv"


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def download() -> None:
    if CSV_PATH.exists() and CSV_PATH.stat().st_size == EXPECTED_BYTES:
        log(f"already downloaded: {CSV_PATH} ({CSV_PATH.stat().st_size} bytes)")
        return
    log(f"downloading {URL}")
    tmp = CSV_PATH.with_suffix(".csv.part")
    urllib.request.urlretrieve(URL, tmp)
    tmp.rename(CSV_PATH)
    log(f"downloaded {CSV_PATH.stat().st_size} bytes")


def verify() -> None:
    size = CSV_PATH.stat().st_size
    if size != EXPECTED_BYTES:
        log(f"WARNING: byte size {size} != expected {EXPECTED_BYTES} (continuing to row check)")

    import pandas as pd

    df = pd.read_csv(CSV_PATH, usecols=["isFraud"])
    rows, frauds = len(df), int(df["isFraud"].sum())
    log(f"rows={rows} frauds={frauds}")
    assert rows == EXPECTED_ROWS, f"row count {rows} != {EXPECTED_ROWS}"
    assert frauds == EXPECTED_FRAUDS, f"fraud count {frauds} != {EXPECTED_FRAUDS}"
    log("verification PASSED")


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    download()
    verify()
    sys.exit(0)
