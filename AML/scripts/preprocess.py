"""Preprocess PaySim for the FL experiment.

Steps (replicating the TieSet/STADLE setup):
- features: step, amount, oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest
- log1p transform on the heavily skewed money columns (baseline sweep showed this
  is required to reach the TieSet metric profile with logistic regression)
- stratified 80/20 train/test split (global held-out test set)
- global StandardScaler fitted on the train split (documented simplification:
  strict FL would compute federated statistics instead)
- train split shuffled and cut into N IID partitions (default 10)

Outputs: data/partitions/part_<i>.parquet, data/test.parquet, data/scaler.json

Usage: preprocess.py [--num-partitions 10] [--non-iid]
  --non-iid partitions by transaction `type` groups instead of IID shuffle (optional mode).
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

FEATURES = ["step", "amount", "oldbalanceOrg", "newbalanceOrig",
            "oldbalanceDest", "newbalanceDest"]
MONEY = ["amount", "oldbalanceOrg", "newbalanceOrig",
         "oldbalanceDest", "newbalanceDest"]
LABEL = "isFraud"
SEED = 42

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "paysim.csv"
OUT = ROOT / "data"


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--num-partitions", type=int, default=10)
    ap.add_argument("--non-iid", action="store_true")
    ap.add_argument("--partitions-dir", default=None,
                    help="output subdir under data/ (default: partitions, "
                         "or partitions_noniid when --non-iid)")
    args = ap.parse_args()

    log(f"loading {RAW}")
    df = pd.read_csv(RAW, usecols=FEATURES + [LABEL, "type"])
    log(f"loaded {len(df)} rows, frauds={int(df[LABEL].sum())}")
    for col in MONEY:
        df[col] = np.log1p(df[col])

    train_df, test_df = train_test_split(
        df, test_size=0.2, stratify=df[LABEL], random_state=SEED)
    log(f"train={len(train_df)} (frauds={int(train_df[LABEL].sum())}) "
        f"test={len(test_df)} (frauds={int(test_df[LABEL].sum())})")

    scaler = StandardScaler().fit(train_df[FEATURES].to_numpy())
    (OUT / "scaler.json").write_text(json.dumps({
        "features": FEATURES,
        "log1p_columns": MONEY,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
    }, indent=1))

    def scaled(frame: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(scaler.transform(frame[FEATURES].to_numpy()),
                           columns=FEATURES)
        out[LABEL] = frame[LABEL].to_numpy()
        return out

    test_out = scaled(test_df)
    test_out.to_parquet(OUT / "test.parquet", index=False)
    log(f"wrote test.parquet ({len(test_out)} rows)")

    subdir = args.partitions_dir or ("partitions_noniid" if args.non_iid
                                     else "partitions")
    part_dir = OUT / subdir
    part_dir.mkdir(exist_ok=True)
    n = args.num_partitions
    train_df = train_df.reset_index(drop=True)
    if args.non_iid:
        # Dirichlet split per transaction type: each client gets a different
        # type mix (banks with different business profiles). Fraud exists only
        # in CASH_OUT/TRANSFER, so fraud exposure varies strongly per client.
        rng = np.random.default_rng(SEED)
        client_indices: list[list[int]] = [[] for _ in range(n)]
        for _, group in train_df.groupby("type"):
            idx = rng.permutation(group.index.to_numpy())
            proportions = rng.dirichlet([0.5] * n)
            cuts = (np.cumsum(proportions)[:-1] * len(idx)).astype(int)
            for client, chunk in enumerate(np.split(idx, cuts)):
                client_indices[client].extend(chunk.tolist())
        shards = [train_df.iloc[sorted(ix)] for ix in client_indices]
    else:
        train_df = (train_df.sample(frac=1.0, random_state=SEED)
                    .reset_index(drop=True))
        shards = [train_df.iloc[idx]
                  for idx in np.array_split(np.arange(len(train_df)), n)]

    for i, shard in enumerate(shards):
        out = scaled(shard)
        frauds = int(out[LABEL].sum())
        assert frauds >= 2, f"part_{i} has {frauds} fraud rows; LR needs both classes"
        out.to_parquet(part_dir / f"part_{i}.parquet", index=False)
        log(f"part_{i}: rows={len(out)} frauds={frauds}")

    log("preprocess DONE")


if __name__ == "__main__":
    main()
