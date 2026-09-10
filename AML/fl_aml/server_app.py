"""Flower ServerApp: FedAvg with per-client metric capture (local models) and
centralized evaluation of the aggregated model each round (the blue line)."""

import json
import time
from pathlib import Path

from flwr.app import ArrayRecord, Context, MetricRecord
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg

from fl_aml.task import (MLP, classification_metrics, create_lr, get_lr_params,
                         initial_lr_params, load_test, predict_mlp,
                         set_lr_params)

app = ServerApp()


def _log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [server] {msg}", flush=True)


class MetricsCapturingFedAvg(FedAvg):
    """FedAvg that persists each client's self-reported metrics every round."""

    def __init__(self, results_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.results_dir = results_dir
        self.local_metrics: list[dict] = []

    def aggregate_train(self, server_round, replies):
        replies = list(replies)
        for reply in replies:
            if reply.has_content() and "metrics" in reply.content:
                rec = dict(reply.content["metrics"])
                self.local_metrics.append({"round": server_round, **rec})
        (self.results_dir / "local_metrics.json").write_text(
            json.dumps(self.local_metrics, indent=1))
        _log(f"round {server_round}: captured {len(replies)} client replies")
        return super().aggregate_train(server_round, replies)


@app.main()
def main(grid: Grid, context: Context) -> None:
    cfg = context.run_config
    model_type = str(cfg["model-type"])
    results_dir = Path(str(cfg["results-dir"]))
    results_dir.mkdir(parents=True, exist_ok=True)

    X_test, y_test = load_test(str(cfg["data-dir"]))
    _log(f"model={model_type} rounds={cfg['num-server-rounds']} "
         f"test_rows={len(X_test)}")

    if model_type == "logreg":
        initial_arrays = ArrayRecord(initial_lr_params())
    else:
        initial_arrays = ArrayRecord(MLP().state_dict())

    aggregated_metrics: list[dict] = []

    def evaluate_fn(server_round: int, arrays: ArrayRecord):
        if model_type == "logreg":
            model = create_lr(1, str(cfg["class-weight"]))
            set_lr_params(model, arrays.to_numpy_ndarrays())
            y_pred = model.predict(X_test)
        else:
            model = MLP()
            model.load_state_dict(arrays.to_torch_state_dict())
            y_pred = predict_mlp(model, X_test)
        rec = {"round": server_round, **classification_metrics(y_test, y_pred)}
        aggregated_metrics.append(rec)
        (results_dir / "aggregated_metrics.json").write_text(
            json.dumps(aggregated_metrics, indent=1))
        _log(f"aggregated model round {server_round}: {rec}")
        return MetricRecord({k: v for k, v in rec.items() if k != "round"})

    strategy = MetricsCapturingFedAvg(
        results_dir=results_dir,
        fraction_train=1.0,
        fraction_evaluate=0.0,
        min_train_nodes=int(cfg.get("min-nodes", 10)),
        min_available_nodes=int(cfg.get("min-nodes", 10)),
    )
    result = strategy.start(
        grid=grid,
        initial_arrays=initial_arrays,
        num_rounds=int(cfg["num-server-rounds"]),
        evaluate_fn=evaluate_fn,
    )

    final_arrays = result.arrays.to_numpy_ndarrays()
    import pickle
    (results_dir / "final_model.pkl").write_bytes(pickle.dumps(final_arrays))
    _log("run complete; final model saved")
