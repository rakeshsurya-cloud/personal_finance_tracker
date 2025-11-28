"""
process_transactions.py
-----------------------
Scan a directory of bank or credit card statements, classify each
transaction using a trained text model and produce combined CSV and
dashboard outputs.
"""

from __future__ import annotations

import argparse
import glob
import os
import pickle
from pathlib import Path
from typing import Optional, List

import pandas as pd
from sqlalchemy.orm import Session
from database import Transaction, SessionLocal

# Patterns used to identify columns.
DESCRIPTION_PATTERNS = ["description", "details", "name", "memo", "transaction", "merchant"]
DATE_PATTERNS = ["date", "transaction date", "posted", "post date", "value date"]
AMOUNT_PATTERNS = ["amount", "debit", "credit", "amount $", "amt", "withdrawal", "deposit"]

def infer_column(df: pd.DataFrame, patterns: list[str]) -> Optional[str]:
    for pattern in patterns:
        for col in df.columns:
            if pattern in col.lower():
                return col
    return None

def parse_statement(path: Path) -> Optional[pd.DataFrame]:
    try:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        elif path.suffix.lower() in (".xls", ".xlsx"):
            df = pd.read_excel(path)
        else:
            return None
    except Exception as exc:
        print(f"Failed to read {path}: {exc}")
        return None

    if df.empty:
        return None

    date_col = infer_column(df, DATE_PATTERNS)
    desc_col = infer_column(df, DESCRIPTION_PATTERNS)
    amount_col = infer_column(df, AMOUNT_PATTERNS)

    if not date_col or not desc_col:
        return None

    debit_col = None
    credit_col = None
    for c in df.columns:
        lc = c.lower()
        if "debit" in lc or "withdrawal" in lc:
            debit_col = c
        if "credit" in lc or "deposit" in lc:
            credit_col = c
    
    out = pd.DataFrame()
    out["Date"] = pd.to_datetime(df[date_col], errors="coerce")
    out["Description"] = df[desc_col].astype(str)

    if debit_col is not None and credit_col is not None:
        debit = pd.to_numeric(df[debit_col], errors="coerce").fillna(0)
        credit = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)
        out["Amount"] = credit - debit
    else:
        amt_series = df[amount_col].astype(str).str.replace(r"[\$,]", "", regex=True)
        amt_series = amt_series.str.replace(r"\((.*?)\)", r"-\1", regex=True)
        out["Amount"] = pd.to_numeric(amt_series, errors="coerce").fillna(0)

    out = out.dropna(subset=["Date", "Description"])
    return out

def load_model(model_path: str):
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    return model

def classify_transactions(df: pd.DataFrame, model) -> pd.DataFrame:
    if df.empty:
        return df
    X = df["Description"].astype(str)
    predicted = model.predict(X)
    df = df.copy()
    df["Category"] = predicted
    return df

def process_files(files: List[Path], model_path: str) -> pd.DataFrame:
    """Process a list of file paths and return a categorized DataFrame."""
    model = load_model(model_path)
    all_rows = []
    for file in files:
        df = parse_statement(file)
        if df is not None:
            all_rows.append(df)

    if not all_rows:
        return pd.DataFrame()

    combined = pd.concat(all_rows, ignore_index=True)
    combined = combined.drop_duplicates(subset=["Date", "Description", "Amount"])
    combined = combined.sort_values("Date")

    categorized = classify_transactions(combined, model)
    return categorized

def save_to_db(df: pd.DataFrame, db: Session):
    """Saves the DataFrame to the database, avoiding duplicates."""
    count = 0
    for _, row in df.iterrows():
        # Check for existing transaction (simple check by date, desc, amount)
        # In a real app, we'd want a more robust ID or hash.
        exists = db.query(Transaction).filter(
            Transaction.date == row["Date"].date(),
            Transaction.description == row["Description"],
            Transaction.amount == row["Amount"]
        ).first()
        
        if not exists:
            txn = Transaction(
                date=row["Date"].date(),
                description=row["Description"],
                amount=row["Amount"],
                category=row["Category"],
                source="csv_upload",
                is_shared=False # Default to private
            )
            db.add(txn)
            count += 1
    db.commit()
    return count