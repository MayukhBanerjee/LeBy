"""
legal_issue_classifier.py
---------------------------------
A tiny, standalone ML playground module for your repo.

What it does:
- Builds a scikit-learn text classifier to label short legal situations
  (Traffic/Accident, Police/Criminal, Landlord/Tenant, Employment, Consumer/Contract, Family)
- Trains on a small in-memory dataset (no files needed)
- Evaluates with a classification report + confusion matrix
- Saves/loads the model artifact
- Predicts labels for new texts (CLI + importable functions)

Usage (from backend/):
    # Train and evaluate, then save model
    python -m ml_playground.legal_issue_classifier train

    # Evaluate on the holdout set (loads artifact if available or retrains if not)
    python -m ml_playground.legal_issue_classifier eval

    # Predict a label for a snippet
    python -m ml_playground.legal_issue_classifier predict "I rear-ended a car at a signal; insurance wants a statement."

Integration:
- This module is self-contained and **does not affect** your FastAPI or Gemini code.
- You can import predict_text() elsewhere if you want optional hooks.

Requirements (add to your backend env if needed):
    pip install scikit-learn==1.4.2 joblib==1.3.2
"""

from __future__ import annotations
import argparse
import os
import sys
from dataclasses import dataclass
from typing import List, Tuple, Dict

import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier  # logistic regression via log loss


# ----------------------------
# Config / Artifacts location
# ----------------------------
SEED = 42
ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "ml_artifacts")
MODEL_PATH = os.path.abspath(os.path.join(ARTIFACT_DIR, "legal_issue_clf.pkl"))


# ----------------------------
# Tiny in-memory dataset
# ----------------------------
@dataclass(frozen=True)
class Example:
    text: str
    label: str


def _dataset() -> List[Example]:
    """Small, hand-written examples for quick demos. Extend freely."""
    return [
        # Traffic / Accident
        Example("Car accident at junction; other driver ran a red light; insurance asking for statement", "Traffic/Accident"),
        Example("Got a speeding ticket and court date next month", "Traffic/Accident"),
        Example("Minor collision in parking lot, need to file a police report and claim", "Traffic/Accident"),
        Example("Bike accident with pedestrian; hospital bills and liability question", "Traffic/Accident"),
        Example("Hit-and-run; I have dashcam footage and number plate", "Traffic/Accident"),
        Example("Rear-ended on the highway, adjuster wants recorded call", "Traffic/Accident"),

        # Police / Criminal
        Example("Police stopped me and searched my bag without a warrant", "Police/Criminal"),
        Example("Received a notice for court appearance in a misdemeanor case", "Police/Criminal"),
        Example("Friend arrested last night; need bail information", "Police/Criminal"),
        Example("Summoned for questioning in a criminal investigation", "Police/Criminal"),
        Example("Charged with petty theft; first-time offense; options?", "Police/Criminal"),
        Example("Got a criminal summons; what are the next steps?", "Police/Criminal"),

        # Landlord / Tenant
        Example("Landlord not returning my security deposit after move-out", "Landlord/Tenant"),
        Example("Eviction notice due to late rent; need to know rights", "Landlord/Tenant"),
        Example("Water leakage and mold; landlord ignoring repair requests", "Landlord/Tenant"),
        Example("Roommate refuses to leave; sublease unclear", "Landlord/Tenant"),
        Example("Rent hike without notice; is this legal?", "Landlord/Tenant"),
        Example("Lease termination terms and early exit penalty", "Landlord/Tenant"),

        # Employment
        Example("Unpaid overtime; employer says I'm exempt", "Employment"),
        Example("Wrongful termination after medical leave", "Employment"),
        Example("Harassment by supervisor; HR complaint filed", "Employment"),
        Example("Offer letter rescinded; can I claim damages?", "Employment"),
        Example("Non-compete clause restricting new job", "Employment"),
        Example("Denied benefits; misclassification as contractor", "Employment"),

        # Consumer / Contract
        Example("Service provider breached contract; refund requested", "Consumer/Contract"),
        Example("Online purchase defective; seller refusing replacement", "Consumer/Contract"),
        Example("Subscription auto-renewed without consent", "Consumer/Contract"),
        Example("Builder missed delivery deadline; penalty clause", "Consumer/Contract"),
        Example("Warranty claim denied for a new phone", "Consumer/Contract"),
        Example("Loan agreement terms unclear; hidden charges", "Consumer/Contract"),

        # Family
        Example("Child custody schedule needs modification", "Family"),
        Example("Mutual divorce paperwork and timelines", "Family"),
        Example("Domestic dispute; need protective order info", "Family"),
        Example("Alimony amount revision after job loss", "Family"),
        Example("Adoption process and required documents", "Family"),
        Example("Name change after marriage; steps involved", "Family"),
    ]


# ----------------------------
# Model building
# ----------------------------
def build_pipeline() -> Pipeline:
    """
    Text -> TF-IDF -> Linear classifier (SGD with log loss ~ logistic regression).
    We keep it simple and fast, with calibrated decision_function for confidence.
    """
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.9,
                sublinear_tf=True,
                lowercase=True,
                stop_words="english")),
            ("clf", SGDClassifier(
                loss="log_loss",  # logistic regression
                alpha=1e-4,
                max_iter=2000,
                tol=1e-3,
                random_state=SEED))
        ]
    )


def train_model() -> Tuple[Pipeline, Dict[str, int]]:
    data = _dataset()
    X = [ex.text for ex in data]
    y = [ex.label for ex in data]

    labels = sorted(list(set(y)))
    label_to_id = {lbl: i for i, lbl in enumerate(labels)}
    y_int = np.array([label_to_id[lbl] for lbl in y])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_int, test_size=0.25, random_state=SEED, stratify=y_int
    )

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    # Evaluate
    y_pred = pipe.predict(X_test)
    print("\n=== Evaluation (holdout) ===")
    print(classification_report(y_test, y_pred, target_names=labels, digits=3))
    print("Confusion matrix (rows=true, cols=pred):")
    print(confusion_matrix(y_test, y_pred))

    # Persist artifacts
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    joblib.dump({"model": pipe, "labels": labels}, MODEL_PATH)
    print(f"\nSaved model to: {MODEL_PATH}")

    return pipe, label_to_id


def load_model() -> Tuple[Pipeline, List[str]]:
    if not os.path.exists(MODEL_PATH):
        print("Model artifact not found; training a fresh one...")
        pipe, label_to_id = train_model()
        labels = [None] * len(label_to_id)
        for k, v in label_to_id.items():
            labels[v] = k
        return pipe, labels

    bundle = joblib.load(MODEL_PATH)
    return bundle["model"], bundle["labels"]


def predict_text(text: str) -> Dict[str, str]:
    """
    Predict the legal issue label for a given text.
    Returns: {"label": str, "confidence": float (0..1)}
    """
    if not text or not text.strip():
        return {"label": "Unknown", "confidence": 0.0}

    model, labels = load_model()
    pred = model.predict([text])[0]
    # Use decision_function to get a pseudo-confidence; softmax-ish normalization
    scores = model.decision_function([text])[0]
    if scores.ndim == 0:  # binary edge-case
        scores = np.array([scores, -scores])
    exp = np.exp(scores - scores.max())
    probs = exp / exp.sum()
    confidence = float(probs[pred])

    return {"label": labels[pred], "confidence": round(confidence, 4)}


# ----------------------------
# CLI
# ----------------------------
def _cli():
    parser = argparse.ArgumentParser(
        description="Tiny ML playground: legal issue text classifier"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("train", help="Train and evaluate, then save the model")
    sub.add_parser("eval", help="Evaluate on the holdout set (loads or trains)")
    p_predict = sub.add_parser("predict", help="Predict a label for given text")
    p_predict.add_argument("text", type=str, help="Input text to classify")

    args = parser.parse_args()
    if args.cmd == "train":
        train_model()
    elif args.cmd == "eval":
        # Quick eval by retraining then testing ensures consistency for this tiny dataset
        train_model()
    elif args.cmd == "predict":
        res = predict_text(args.text)
        print(res)
    else:
        parser.print_help()


if __name__ == "__main__":
    # Allow running via:
    #   python ml_playground/legal_issue_classifier.py predict "text..."
    # or:
    #   python -m ml_playground.legal_issue_classifier predict "text..."
    # from the backend/ directory.
    sys.exit(_cli())
