"""
train_classifier.py
--------------------

This script trains a simple text classifier to categorize transaction
descriptions into spending categories.  It uses scikit‑learn's
``TfidfVectorizer`` to convert free‑form text into numerical features
and a multinomial logistic regression model to perform multi‑class
classification.  The resulting vectorizer and model are serialized to
disk using pickle so they can be reloaded later when processing
transaction data.

By default, it trains on the sample training data defined in
``training_data.py``.  If you wish to supply your own labeled data
instead, you can provide a CSV file with two columns: ``Description``
and ``Category``.  Pass the path to that CSV as the ``--data``
argument when running this script.

Usage:

    python train_classifier.py [--data custom_training.csv] [--model-output models/model.pkl]

The script will create the output directory if it does not already
exist.
"""

import argparse
import os
import pickle
from typing import Tuple

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from training_data import TRAINING_DATA


def load_training_data(path: str | None) -> pd.DataFrame:
    """Load training data from a CSV or from the built‑in sample list.

    Args:
        path: Optional path to a CSV file containing labelled data.  The
            file must contain at least two columns named ``Description`` and
            ``Category``.

    Returns:
        A pandas DataFrame with ``Description`` and ``Category`` columns.
    """
    if path:
        df = pd.read_csv(path)
        if not {"Description", "Category"}.issubset(set(df.columns)):
            raise ValueError("Custom training CSV must contain Description and Category columns")
        df = df[["Description", "Category"]].dropna()
    else:
        # Use built‑in training examples
        df = pd.DataFrame(TRAINING_DATA, columns=["Description", "Category"])
    return df


def build_model() -> Pipeline:
    """Create the classification pipeline.

    Returns:
        A scikit‑learn Pipeline that vectorizes text and applies a
        logistic regression classifier.
    """
    # The TfidfVectorizer converts raw text into a sparse matrix of TF‑IDF
    # features.  We strip accents, remove English stop words and
    # consider unigrams and bigrams to capture short phrases like
    # "credit card".  Limiting the vocabulary size helps control memory
    # usage and training time.
    vectorizer = TfidfVectorizer(
        strip_accents="unicode",
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        max_features=5000,
    )

    classifier = LogisticRegression(max_iter=1000, multi_class="auto")

    return Pipeline([
        ("vectorizer", vectorizer),
        ("classifier", classifier),
    ])


def train_and_save(model: Pipeline, data: pd.DataFrame, output_path: str) -> None:
    """Train the model on the provided data and save it to disk.

    Args:
        model: A scikit‑learn Pipeline containing a vectorizer and classifier.
        data: Training DataFrame with ``Description`` and ``Category`` columns.
        output_path: Path to the pickle file to create.  Parent
            directories will be created if necessary.
    """
    X = data["Description"].astype(str)
    y = data["Category"].astype(str)
    model.fit(X, y)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(model, f)

    print(f"Model trained on {len(data)} samples and saved to {output_path}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Train a transaction description classifier")
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Optional CSV file containing custom labelled training data."
    )
    parser.add_argument(
        "--model-output",
        type=str,
        default="personal_finance_tracker/models/transaction_classifier.pkl",
        help="Path to save the trained model (pickle file)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_training_data(args.data)
    model = build_model()
    train_and_save(model, df, args.model_output)


if __name__ == "__main__":
    main()