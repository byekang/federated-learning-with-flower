# Federated Learning for AML Fraud Detection (Flower + PaySim)

A hands-on lab of **Federated Learning (FL)** applied to AML (Anti-Money
Laundering) fraud detection, built on the [Flower](https://flower.ai)
framework and the PaySim synthetic transaction dataset. It runs a real
distributed deployment - one SuperLink (server) and ten SuperNodes (clients)
communicating over gRPC - rather than an in-process simulation, so the same
setup scales to multiple machines by changing addresses only.

Everything is driven by the guided Jupyter notebook,
**`fl_aml_hands_on.ipynb`**, which makes FL's value visible: banks that train
alone on scarce fraud labels fail, while the federated model is strong for
every participant - shown as cross-evaluation heatmaps, confusion matrices,
and convergence charts.

This folder is self-contained: everything the notebook needs lives here, and
the dataset (~470 MB) is downloaded during the lab.

## Results at a Glance

10 virtual banks, non-IID data (Dirichlet split by transaction type), evaluated
on a held-out global test set of 1.27M transactions (1,643 frauds):

| Model | Precision | Recall | F1 |
|---|---|---|---|
| Best solo bank (logistic regression, own data only) | 0.974 | 0.487 | 0.649 |
| Worst solo bank (logistic regression, own data only) | 0.988 | 0.051 | 0.097 |
| Solo MLP, best-endowed bank (60 epochs) | - | - | 0.594 |
| **Federated MLP (10 banks, 10 rounds, FedAvg)** | **0.975** | **0.671** | **~0.79** |

A bank holding only 18 confirmed fraud cases ends up with the same ~0.79-F1
model as everyone else - without a single raw transaction leaving its node.

## Architecture

```
flwr run (submits the app bundle)
      |
      v :9093 (Exec API)
+-------------+   ServerApp: FedAvg aggregation
|  SuperLink  |   + centralized evaluation on the global test set
+-------------+   + per-round metrics persisted to JSON
      ^ :9092 (Fleet API, gRPC - only model parameters travel)
      |
 SN-0 ... SN-9    10 SuperNodes = 10 banks (ports 9094-9103 on one host)
 part_0 .. part_9 each node reads only its own partition
```

## Quickstart

Requirements: Linux, Python >= 3.11, ~2 GB of free disk for the dataset.

```bash
git clone https://github.com/byekang/federated-learning-with-flower
cd federated-learning-with-flower/AML

# 1. Environment (creates the venv and registers the notebook kernel)
python3 -m venv --system-site-packages .venv
.venv/bin/pip install "flwr==1.36.0" pyarrow scikit-learn pandas torch matplotlib ipykernel
.venv/bin/python -m ipykernel install --user --name fl-aml --display-name "Python (fl-AML)"
```

Note: on hosts with a pre-populated Python environment (e.g. SageMaker
Studio's conda base), pip may print a dependency-resolver "ERROR" about
unrelated system packages (such as `typer-slim` requiring a newer `typer`).
As long as the log ends with `Successfully installed ... flwr-1.36.0 ...`,
this is harmless for the lab - nothing here uses those packages.

Then open `fl_aml_hands_on.ipynb` with the **Python (fl-AML)** kernel.

If you are already inside a Jupyter environment (SageMaker Studio, JupyterHub,
VS Code, ...), no further setup is needed - refresh the kernel list and select
the kernel. Only on a bare machine with no Jupyter running, install and start
one:

```bash
.venv/bin/pip install jupyterlab
.venv/bin/python -m jupyterlab --no-browser
```

The notebook walks through everything else: downloading and verifying the
dataset, partitioning it into 10 virtual banks, training solo baselines,
starting the federation (terminal steps are clearly marked), running FedAvg,
and visualizing the before/after comparison.

To run experiments without the notebook:

```bash
.venv/bin/python scripts/download_data.py
.venv/bin/python scripts/preprocess.py            # IID partitions
.venv/bin/python scripts/preprocess.py --non-iid  # non-IID partitions

bash scripts/start_superlink.sh
bash scripts/start_supernodes.sh 10
bash scripts/status_check.sh                      # liveness, ports, progress

# model, rounds, nodes, partition set, results name
bash scripts/run_experiment.sh logreg 10 10
bash scripts/run_experiment.sh mlp 10 10 partitions_noniid mlp_noniid

bash scripts/stop_all.sh
```

## Folder Layout

```
fl_aml_hands_on.ipynb   guided hands-on notebook (start here)
pyproject.toml          Flower app definition + run-config defaults
fl_aml/
  task.py               features, LR/MLP models, parameter round-trip, metrics
  client_app.py         ClientApp: local training + self-evaluation per round
  server_app.py         ServerApp: FedAvg subclass with dual metric capture
scripts/
  download_data.py      dataset download + integrity verification
  preprocess.py         log1p + scaling, train/test split, IID / non-IID partitioning
  start_superlink.sh, start_supernodes.sh, stop_all.sh, status_check.sh
  run_experiment.sh     flwr run wrapper (injects absolute paths, logs to logs/)
```

Experiment outputs land in `results/<name>/` as `aggregated_metrics.json`
(server-side evaluation of the global model per round), `local_metrics.json`
(every client's self-evaluation per round), and `final_model.pkl`. The
`data/`, `logs/`, and `results/` directories are created during the lab and
excluded from git.

## Scaling to Multiple Machines

The single-host lab is architecturally identical to a multi-machine
deployment. To distribute it:

1. Run `flower-superlink` on one server; open inbound 9092 (from clients) and
   9093 (from wherever you submit runs).
2. Run one `flower-supernode --superlink <server-ip>:9092` per client machine.
   SuperNodes need **outbound connectivity only** - no inbound ports - which
   fits financial-institution firewall policies well.
3. Distribute each partition file to its owning machine and reference it via
   `--node-config "partition-id=N num-partitions=10"`.
4. For production, replace `--insecure` with TLS
   (`--ssl-ca-certfile / --ssl-certfile / --ssl-keyfile` on the SuperLink,
   `--root-certificates` on each SuperNode) and enable SuperNode
   authentication.

## Dataset and Acknowledgements

- **PaySim**: E. A. Lopez-Rojas, A. Elmir, and S. Axelsson, "PaySim: A
  financial mobile money simulator for fraud detection" (EMSS 2016).
  Published on Kaggle as [`ealaxi/paysim1`](https://www.kaggle.com/ealaxi/paysim1);
  downloaded here from a public HuggingFace mirror
  ([`theman10/paysim`](https://huggingface.co/datasets/theman10/paysim)).
  6,362,620 transactions, 8,213 labeled frauds.
- **Flower** federated learning framework: https://flower.ai (Apache-2.0).
- The IID logistic-regression experiment replicates the setup described in a
  STADLE (TieSet Inc.) case study of FL for AML on PaySim.

This lab uses synthetic data only and is intended for education and research
on privacy-preserving machine learning. The code in this folder is provided
under the Apache License 2.0.
