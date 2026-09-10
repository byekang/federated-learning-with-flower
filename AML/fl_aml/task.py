"""Shared model/data utilities for the FL AML demo."""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score

warnings.filterwarnings("ignore", category=ConvergenceWarning)

FEATURES = ["step", "amount", "oldbalanceOrg", "newbalanceOrig",
            "oldbalanceDest", "newbalanceDest"]
LABEL = "isFraud"


# ---------------------------------------------------------------- data

def load_partition(data_dir: str, partition_id: int,
                   partitions_dir: str = "partitions"):
    df = pd.read_parquet(Path(data_dir) / partitions_dir / f"part_{partition_id}.parquet")
    return df[FEATURES].to_numpy(), df[LABEL].to_numpy()


def load_test(data_dir: str):
    df = pd.read_parquet(Path(data_dir) / "test.parquet")
    return df[FEATURES].to_numpy(), df[LABEL].to_numpy()


def classification_metrics(y_true, y_pred) -> dict:
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


# ---------------------------------------------------------------- logistic regression

def create_lr(local_epochs: int, class_weight: str) -> LogisticRegression:
    model = LogisticRegression(
        solver="lbfgs",
        max_iter=local_epochs,
        warm_start=True,
        class_weight=None if class_weight == "none" else class_weight,
    )
    set_lr_params(model, initial_lr_params())
    return model


def initial_lr_params() -> list[np.ndarray]:
    return [np.zeros((1, len(FEATURES))), np.zeros(1)]


def get_lr_params(model: LogisticRegression) -> list[np.ndarray]:
    return [model.coef_, model.intercept_]


def set_lr_params(model: LogisticRegression, ndarrays: list[np.ndarray]) -> None:
    model.coef_ = np.asarray(ndarrays[0])
    model.intercept_ = np.asarray(ndarrays[1])
    model.classes_ = np.array([0, 1])


# ---------------------------------------------------------------- MLP (PyTorch)

class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(len(FEATURES), 32), nn.ReLU(),
            nn.Linear(32, 16), nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_mlp(model: MLP, X, y, epochs: int, lr: float = 1e-3,
              batch_size: int = 8192) -> None:
    torch.set_num_threads(2)  # 10 client processes share 16 vCPUs
    device = torch.device("cpu")
    model.to(device).train()
    Xt = torch.tensor(X, dtype=torch.float32)
    yt = torch.tensor(y, dtype=torch.float32)
    ds = torch.utils.data.TensorDataset(Xt, yt)
    loader = torch.utils.data.DataLoader(ds, batch_size=batch_size, shuffle=True)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()
    for _ in range(epochs):
        for xb, yb in loader:
            opt.zero_grad()
            loss_fn(model(xb), yb).backward()
            opt.step()


@torch.no_grad()
def predict_mlp(model: MLP, X, batch_size: int = 65536) -> np.ndarray:
    model.eval()
    Xt = torch.tensor(X, dtype=torch.float32)
    preds = []
    for i in range(0, len(Xt), batch_size):
        logits = model(Xt[i:i + batch_size])
        preds.append((torch.sigmoid(logits) >= 0.5).numpy().astype(int))
    return np.concatenate(preds)
