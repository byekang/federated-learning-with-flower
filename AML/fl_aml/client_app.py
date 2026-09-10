"""Flower ClientApp: local training + self-evaluation of the freshly trained
local model on the global held-out test set (the orange lines in the report)."""

from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

from fl_aml.task import (MLP, classification_metrics, create_lr, get_lr_params,
                         load_partition, load_test, predict_mlp, set_lr_params,
                         train_mlp)

app = ClientApp()


@app.train()
def train(msg: Message, context: Context) -> Message:
    cfg = context.run_config
    partition_id = int(context.node_config["partition-id"])

    X_train, y_train = load_partition(cfg["data-dir"], partition_id,
                                      str(cfg.get("partitions-dir", "partitions")))
    X_test, y_test = load_test(cfg["data-dir"])

    if cfg["model-type"] == "logreg":
        model = create_lr(int(cfg["local-epochs"]), str(cfg["class-weight"]))
        set_lr_params(model, msg.content["arrays"].to_numpy_ndarrays())
        model.fit(X_train, y_train)
        arrays = ArrayRecord(get_lr_params(model))
        y_pred = model.predict(X_test)
    else:
        model = MLP()
        model.load_state_dict(msg.content["arrays"].to_torch_state_dict())
        train_mlp(model, X_train, y_train, epochs=int(cfg["local-epochs"]))
        arrays = ArrayRecord(model.state_dict())
        y_pred = predict_mlp(model, X_test)

    metrics = MetricRecord({
        "num-examples": len(X_train),
        "partition-id": partition_id,
        **classification_metrics(y_test, y_pred),
    })
    return Message(RecordDict({"arrays": arrays, "metrics": metrics}), reply_to=msg)
