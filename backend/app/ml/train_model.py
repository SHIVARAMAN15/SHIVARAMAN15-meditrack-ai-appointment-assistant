"""
Train and evaluate attendance prediction model using scikit-learn.
Compares a baseline Logistic Regression model with a Random Forest Classifier.
Saves model artifacts and performance metrics without data leakage.
"""
import os
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)
import joblib

try:
    from app.ml.generate_data import generate_synthetic_data, ALLOWED_DEPARTMENTS
except ImportError:
    from generate_data import generate_synthetic_data, ALLOWED_DEPARTMENTS

FEATURE_COLUMNS = [
    "lead_time_days",
    "day_of_week",
    "appointment_hour",
    "previous_appointments",
    "previous_no_shows",
    "had_previous_reminder",
    "department"
]

NUMERIC_FEATURES = [
    "lead_time_days",
    "day_of_week",
    "appointment_hour",
    "previous_appointments",
    "previous_no_shows",
    "had_previous_reminder"
]

CATEGORICAL_FEATURES = ["department"]

def create_preprocessor():
    """Build unified feature preprocessor inside pipeline to prevent data leakage."""
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(categories=[ALLOWED_DEPARTMENTS], handle_unknown="ignore"), CATEGORICAL_FEATURES)
        ]
    )

def train_and_evaluate(dataset_path: Path = None):
    """Execute training pipeline, compare models, and persist best model."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    workspace_root = backend_dir.parent
    artifacts_dir = backend_dir / "app" / "ml" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if dataset_path is None or not Path(dataset_path).exists():
        data_dir = workspace_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        dataset_path = data_dir / "synthetic_appointments.csv"
        if not dataset_path.exists():
            print("Dataset not found. Generating fresh synthetic dataset...")
            df = generate_synthetic_data(num_samples=1500, random_seed=42)
            df.to_csv(dataset_path, index=False)
        else:
            df = pd.read_csv(dataset_path)
    else:
        df = pd.read_csv(dataset_path)

    X = df[FEATURE_COLUMNS]
    y = df["attended"]

    # Stratified 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    models = {
        "LogisticRegression": Pipeline([
            ("preprocessor", create_preprocessor()),
            ("classifier", LogisticRegression(random_state=42, max_iter=1000))
        ]),
        "RandomForest": Pipeline([
            ("preprocessor", create_preprocessor()),
            ("classifier", RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                min_samples_split=4,
                random_state=42
            ))
        ])
    }

    eval_results = {}

    print("==================================================")
    print(" MediTrack AI Attendance Model Evaluation")
    print("==================================================")

    for name, pipeline in models.items():
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)[:, 1]

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        roc_auc = float(roc_auc_score(y_test, y_prob))
        cm = confusion_matrix(y_test, y_pred).tolist()

        eval_results[name] = {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "roc_auc": roc_auc,
            "confusion_matrix": cm,
            "pipeline": pipeline
        }

        print(f"\n--- {name} Results ---")
        print(f"Accuracy:  {acc:.4f}")
        print(f"Precision: {prec:.4f}")
        print(f"Recall:    {rec:.4f}")
        print(f"F1 Score:  {f1:.4f}")
        print(f"ROC-AUC:   {roc_auc:.4f}")
        print(f"Confusion Matrix (TN, FP / FN, TP):\n  {cm[0]}\n  {cm[1]}")

    # Select best model based on ROC-AUC and F1 balance
    # Random Forest typically captures slight non-linear interactions while maintaining fast (<5ms) inference
    selected_name = "RandomForest" if eval_results["RandomForest"]["roc_auc"] >= eval_results["LogisticRegression"]["roc_auc"] else "LogisticRegression"
    best = eval_results[selected_name]

    print(f"\n>> Selected Model: {selected_name} for production inference.")

    # Save artifact
    model_artifact_path = artifacts_dir / "attendance_model.joblib"
    joblib.dump(best["pipeline"], model_artifact_path)
    print(f">> Model saved to {model_artifact_path}")

    # Save metrics JSON
    metrics_data = {
        "model_name": selected_name,
        "model_version": "v1.0.0",
        "timestamp": pd.Timestamp.utcnow().isoformat(),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "metrics": {
            "accuracy": round(best["accuracy"], 4),
            "precision": round(best["precision"], 4),
            "recall": round(best["recall"], 4),
            "f1_score": round(best["f1_score"], 4),
            "roc_auc": round(best["roc_auc"], 4),
            "confusion_matrix": best["confusion_matrix"]
        },
        "baseline_comparison": {
            "LogisticRegression": {
                "accuracy": round(eval_results["LogisticRegression"]["accuracy"], 4),
                "f1_score": round(eval_results["LogisticRegression"]["f1_score"], 4),
                "roc_auc": round(eval_results["LogisticRegression"]["roc_auc"], 4)
            },
            "RandomForest": {
                "accuracy": round(eval_results["RandomForest"]["accuracy"], 4),
                "f1_score": round(eval_results["RandomForest"]["f1_score"], 4),
                "roc_auc": round(eval_results["RandomForest"]["roc_auc"], 4)
            }
        },
        "features": FEATURE_COLUMNS
    }

    metrics_file = artifacts_dir / "metrics.json"
    with open(metrics_file, "w") as f:
        json.dump(metrics_data, f, indent=2)
    print(f">> Metrics saved to {metrics_file}")

    return metrics_data

if __name__ == "__main__":
    train_and_evaluate()
