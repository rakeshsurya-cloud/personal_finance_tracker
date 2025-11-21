"""
process_transactions.py
-----------------------

Scan a directory of bank or credit card statements, classify each
transaction using a trained text model and produce combined CSV and
dashboard outputs.  The script attempts to infer date, description and
amount columns from a variety of common bank statement formats.  If a
file cannot be parsed it will be skipped with a warning.

Usage::

    python process_transactions.py \
        --input-dir bank_data/ \
        --model personal_finance_tracker/models/transaction_classifier.pkl \
        --output-csv personal_finance_tracker/output/categorized_transactions.csv \
        --dashboard personal_finance_tracker/output/dashboard.html

You can run this script repeatedly; it always rebuilds the output files
from all CSV/XLS/XLSX files in the input directory.
"""

from __future__ import annotations

import argparse
import glob
import os
import pickle
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from dashboard import generate_dashboard


# Patterns used to identify columns.  Expand this list if your bank
# statements use different naming conventions.  All comparisons are
# performed on lower‑case column names.
DESCRIPTION_PATTERNS = [
    "description",
    "details",
    "name",
    "memo",
    "transaction",
    "merchant",
]

DATE_PATTERNS = [
    "date",
    "transaction date",
    "posted",
    "post date",
    "value date",
]

AMOUNT_PATTERNS = [
    "amount",
    "debit",
    "credit",
    "amount $",
    "amt",
    "withdrawal",
    "deposit",
]

def infer_column(df: pd.DataFrame, patterns: list[str]) -> Optional[str]:
    """Return the first column in df whose name contains any of the given patterns.

    Args:
        df: DataFrame whose columns to inspect.
        patterns: List of lower‑case substrings to search for.

    Returns:
        Name of the matching column or None if no match.
    """
    for pattern in patterns:
        for col in df.columns:
            if pattern in col.lower():
                return col
    return None


def parse_statement(path: Path) -> Optional[pd.DataFrame]:
    """Parse a single statement file into a standardized DataFrame.

    Supported formats: CSV (.csv) and Excel (.xls/.xlsx).  The parser
    attempts to identify date, description and amount columns.  If
    inference fails or the file cannot be read, None is returned.

    Args:
        path: Path to the statement file.

    Returns:
        DataFrame with columns Date (datetime64), Description (str), and
        Amount (float) or None if the file could not be parsed.
    """
    try:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        elif path.suffix.lower() in (".xls", ".xlsx"):
            df = pd.read_excel(path)
        else:
            print(f"Skipping unsupported file type: {path}")
            return None
    except Exception as exc:
        print(f"Failed to read {path}: {exc}")
        return None

    if df.empty:
        return None

    # Identify columns
    date_col = infer_column(df, DATE_PATTERNS)
    desc_col = infer_column(df, DESCRIPTION_PATTERNS)
    amount_col = infer_column(df, AMOUNT_PATTERNS)

    if not date_col or not desc_col:
        print(f"Could not identify date/description columns in {path}")
        return None

    # If separate debit and credit columns exist, compute net amount.
    debit_col = None
    credit_col = None
    for c in df.columns:
        lc = c.lower()
        if "debit" in lc or "withdrawal" in lc:
            debit_col = c
        if "credit" in lc or "deposit" in lc:
            credit_col = c
    
    # Build output frame
    out = pd.DataFrame()
    out["Date"] = pd.to_datetime(df[date_col], errors="coerce")
    out["Description"] = df[desc_col].astype(str)

    if debit_col is not None and credit_col is not None:
        # convert to numeric, treating NaN as 0
        debit = pd.to_numeric(df[debit_col], errors="coerce").fillna(0)
        credit = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)
        out["Amount"] = credit - debit
    else:
        # single amount column; convert to float.  Remove commas and parentheses
        amt_series = df[amount_col].astype(str)
        # Remove currency symbols and commas
        amt_series = amt_series.str.replace(r"[\$,]", "", regex=True)
        # Parentheses indicate negatives (e.g. (123.45))
        amt_series = amt_series.str.replace(r"\((.*?)\)", r"-\1", regex=True)
        out["Amount"] = pd.to_numeric(amt_series, errors="coerce").fillna(0)

    # Drop rows with missing dates or descriptions
    out = out.dropna(subset=["Date", "Description"])

    return out


def load_model(model_path: str):
    """Load the pickled classification pipeline."""
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    return model


def classify_transactions(df: pd.DataFrame, model) -> pd.DataFrame:
    """Assign a category to each transaction using the provided model.

    Args:
        df: DataFrame with at least a ``Description`` column.
        model: scikit‑learn Pipeline loaded from disk.

    Returns:
        DataFrame with a new ``Category`` column.
    """
    X = df["Description"].astype(str)
    predicted = model.predict(X)
    df = df.copy()
    df["Category"] = predicted
    return df


def process_directory(input_dir: str, model_path: str) -> pd.DataFrame:
    """Process all statement files in a directory and classify them.

    Args:
        input_dir: Folder containing CSV/XLS/XLSX files.
        model_path: Path to pickled classification pipeline.

    Returns:
        Combined DataFrame of all transactions with categories.
    """
    model = load_model(model_path)
    files = []
    for ext in ("*.csv", "*.xls", "*.xlsx"):
        files.extend(glob.glob(os.path.join(input_dir, ext)))
    files = sorted(set(files))
    all_rows = []
    for file in files:
        df = parse_statement(Path(file))
        if df is not None:
            all_rows.append(df)

    if not all_rows:
        raise RuntimeError(f"No valid statement files found in {input_dir}")

    combined = pd.concat(all_rows, ignore_index=True)
    # Remove duplicate rows (same date, amount and description) to avoid
    # double counting.  Some banks export overlapping time ranges.
    combined = combined.drop_duplicates(subset=["Date", "Description", "Amount"])
    combined = combined.sort_values("Date")

    categorized = classify_transactions(combined, model)
    return categorized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process and categorize bank statements")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="personal_finance_tracker/bank_data",
        help="Directory containing bank statement files (.csv, .xls, .xlsx)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="personal_finance_tracker/models/transaction_classifier.pkl",
        help="Path to pickled text classification model",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="personal_finance_tracker/output/categorized_transactions.csv",
        help="Where to write the combined, categorized CSV",
    )
    parser.add_argument(
        "--dashboard",
        type=str,
        default="personal_finance_tracker/output/dashboard.html",
        help="Where to write the HTML dashboard",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    categorized = process_directory(args.input_dir, args.model)
    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
    categorized.to_csv(args.output_csv, index=False)
    print(f"Wrote categorized transactions to {args.output_csv}")

    generate_dashboard(args.output_csv, args.dashboard)


if __name__ == "__main__":
    main()