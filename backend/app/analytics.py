"""Reproducible synthetic delay experiment; never predicts merits or verdicts."""
from datetime import date
from functools import lru_cache

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, precision_score, recall_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

VERSION = "synthetic-delay-logistic-v1"
FEATURES = ["days_since_update", "adjournments", "pending_tasks", "missing_documents"]


@lru_cache(maxsize=1)
def train():
    rng = np.random.default_rng(42)
    # Each row is a snapshot at a successive day. Outcome is observed 30 days later.
    x = np.column_stack([rng.integers(0, 100, 900), rng.integers(0, 6, 900), rng.integers(0, 8, 900), rng.integers(0, 5, 900)])
    probability = 1 / (1 + np.exp(-(-3.4 + .032 * x[:, 0] + .25 * x[:, 1] + .29 * x[:, 2] + .36 * x[:, 3])))
    y = (rng.random(900) < probability).astype(int)
    # 30-day embargo ensures training labels precede test snapshot dates.
    train_x, train_y, test_x, test_y = x[:600], y[:600], x[630:], y[630:]
    model = make_pipeline(StandardScaler(), LogisticRegression(random_state=42))
    baseline = DummyClassifier(strategy="prior")
    metrics = {}
    for name, estimator in (("logistic_regression", model), ("baseline_prior", baseline)):
        estimator.fit(train_x, train_y)
        pred, prob = estimator.predict(test_x), estimator.predict_proba(test_x)[:, 1]
        metrics[name] = {"precision": round(precision_score(test_y, pred, zero_division=0), 4),
                         "recall": round(recall_score(test_y, pred, zero_division=0), 4),
                         "f1": round(f1_score(test_y, pred, zero_division=0), 4),
                         "brier_score": round(brier_score_loss(test_y, prob), 4)}
    return model, {"model_version": VERSION, "model_date": "2026-10-10", "seed": 42,
                   "target": "Synthetic procedural milestone NOT completed within 30 days after snapshot (1).",
                   "dataset": "900 fictional daily snapshots; labels sampled from an explicitly synthetic logistic process. No real court data.",
                   "features": FEATURES, "split": "First 600 train; next 30 embargo; final 270 chronological test. No post-snapshot features.",
                   "metrics": metrics, "threshold": 0.5,
                   "limitations": "Synthetic performance is not real-world accuracy. Labels encode designer assumptions. Probabilities are unvalidated for real courts; no priority or merits decisions."}


def indicators(case, tasks):
    days = max(0, (date.today() - date.fromisoformat(case["updated_at"][:10])).days)
    pending = [t for t in tasks if t["case_id"] == case["id"] and t["status"] == "pending"]
    overdue = [t for t in pending if t["deadline"] < str(date.today())]
    reasons = []
    if overdue:
        reasons.append(f"{len(overdue)} overdue procedural task(s)")
    if days > 30:
        reasons.append(f"No recorded update for {days} days")
    if case["adjournments"] >= 2:
        reasons.append(f"{case['adjournments']} simulated adjournments")
    if case["missing_documents"]:
        reasons.append(f"{case['missing_documents']} procedural document gap(s) in sample metadata")
    upcoming = [t for t in pending if str(date.today()) <= t["deadline"] <= str(date.fromordinal(date.today().toordinal() + 3))]
    if upcoming:
        reasons.append(f"{len(upcoming)} configured task deadline(s) within three days")
    return [days, case["adjournments"], len(pending), case["missing_documents"]], reasons


def predict(case, tasks):
    features, reasons = indicators(case, tasks)
    model, _ = train()
    probability = float(model.predict_proba([features])[0, 1])
    return {"case_id": case["id"], "reference": case["reference"], "probability": round(probability, 3),
            "band": "High" if probability >= .65 else "Moderate" if probability >= .35 else "Low",
            "features": dict(zip(FEATURES, features)), "reasons": reasons, "model_version": VERSION,
            "limitations": "Synthetic administrative delay estimate only; not a verdict, legal priority or real-world validated forecast."}