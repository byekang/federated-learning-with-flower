"""Download the PaySim dataset and verify its integrity.

Sources, tried in order:
1. Compressed mirror on S3 (~185 MB gzip, fastest)
2. Raw CSV from the HuggingFace mirror of Kaggle ealaxi/paysim1 (~470 MB)

Hard-fails if the row count or fraud count does not match the published
dataset.
"""

import gzip
import shutil
import sys
import time
import urllib.request
from pathlib import Path

SOURCES = [
    ("https://byekang-share-materials.s3.ap-northeast-2.amazonaws.com"
     "/github-share-files/paysim.csv.gz", True),
    ("https://huggingface.co/datasets/theman10/paysim/resolve/main/paysim.csv",
     False),
]
EXPECTED_BYTES = 493_534_783
EXPECTED_ROWS = 6_362_620
EXPECTED_FRAUDS = 8_213

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
CSV_PATH = DATA_DIR / "paysim.csv"


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def fetch(url: str, gzipped: bool) -> None:
    tmp = CSV_PATH.with_suffix(".csv.part")
    log(f"downloading {url}")
    if gzipped:
        with urllib.request.urlopen(url) as resp, \
                gzip.GzipFile(fileobj=resp) as gz, open(tmp, "wb") as out:
            shutil.copyfileobj(gz, out, length=1 << 20)
    else:
        urllib.request.urlretrieve(url, tmp)
    tmp.rename(CSV_PATH)
    log(f"downloaded {CSV_PATH.stat().st_size} bytes")


def download() -> None:
    if CSV_PATH.exists() and CSV_PATH.stat().st_size == EXPECTED_BYTES:
        log(f"already downloaded: {CSV_PATH} ({CSV_PATH.stat().st_size} bytes)")
        return
    last_error: Exception | None = None
    for url, gzipped in SOURCES:
        try:
            fetch(url, gzipped)
            return
        except Exception as exc:  # noqa: BLE001 - fall through to next mirror
            last_error = exc
            log(f"WARNING: download from {url} failed ({exc}); trying next source")
    raise RuntimeError(f"all download sources failed: {last_error}")


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
