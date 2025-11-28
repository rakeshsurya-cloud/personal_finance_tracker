"""Lightweight MCP-aligned server exposing finance tools over FastAPI."""

from datetime import date
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import FixedExpense, Loan, SessionLocal, Transaction
from insights import detect_anomalies, predict_spending
from loans import simulate_payoff

MODEL_PATH = Path("personal_finance_tracker/models/transaction_classifier.pkl")

app = FastAPI(title="Finance MCP Server", version="0.1.0")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def transactions_to_df(db: Session) -> pd.DataFrame:
    txns = db.query(Transaction).all()
    if not txns:
        return pd.DataFrame(columns=["Date", "Amount", "Category", "Description"])

    df = pd.DataFrame(
        [
            {
                "Date": t.date,
                "Amount": t.amount,
                "Category": t.category or "Uncategorized",
                "Description": t.description or "",
            }
            for t in txns
        ]
    )
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    return df


class PredictCashBalanceRequest(BaseModel):
    period_days: int = Field(30, ge=1, le=365, description="Days to project forward")


class PredictCashBalanceResponse(BaseModel):
    projected_balance: float
    avg_daily_net: float
    sample_days: int
    fixed_expenses: float


@app.post("/tools/predict_cash_balance", response_model=PredictCashBalanceResponse)
async def predict_cash_balance(req: PredictCashBalanceRequest, db: Session = Depends(get_db)):
    df = transactions_to_df(db)
    fixed_total = sum(f.amount for f in db.query(FixedExpense).all())

    if df.empty:
        return PredictCashBalanceResponse(
            projected_balance=-fixed_total,
            avg_daily_net=0.0,
            sample_days=0,
            fixed_expenses=fixed_total,
        )

    df_sorted = df.sort_values("Date")
    daily = df_sorted.groupby("Date")["Amount"].sum()
    daily_window = daily.tail(90)
    avg_daily_net = daily_window.mean()
    current_balance = df_sorted["Amount"].sum()
    projected = current_balance + (avg_daily_net * req.period_days) - (fixed_total * req.period_days / 30)

    return PredictCashBalanceResponse(
        projected_balance=float(projected),
        avg_daily_net=float(avg_daily_net),
        sample_days=len(daily_window),
        fixed_expenses=float(fixed_total),
    )


class DebtInput(BaseModel):
    lender: str
    balance: float
    rate_apr: float
    payment: float


class AvalancheResponse(BaseModel):
    ordered: List[str]
    months_to_payoff: Optional[int]
    total_interest: Optional[float]


@app.post("/tools/calculate_debt_avalanche", response_model=AvalancheResponse)
async def calculate_debt_avalanche(debts: Optional[List[DebtInput]] = None, db: Session = Depends(get_db)):
    debt_rows = debts
    if debt_rows is None:
        debt_rows = [
            DebtInput(lender=l.lender, balance=l.balance, rate_apr=l.interest_rate, payment=l.min_payment)
            for l in db.query(Loan).all()
        ]

    if not debt_rows:
        return AvalancheResponse(ordered=[], months_to_payoff=None, total_interest=None)

    ordered = sorted(debt_rows, key=lambda d: d.rate_apr, reverse=True)
    if len(ordered) == 1:
        schedule = simulate_payoff(ordered[0].balance, ordered[0].rate_apr, ordered[0].payment)
        months = len(schedule) if not schedule.empty else None
        interest = schedule["Interest"].sum() if not schedule.empty else None
    else:
        months = None
        interest = None

    return AvalancheResponse(ordered=[d.lender for d in ordered], months_to_payoff=months, total_interest=interest)


class AnomalyRequest(BaseModel):
    lookback_months: int = Field(6, ge=1, le=12)


class AnomalyResponse(BaseModel):
    alerts: List[str]


@app.post("/tools/get_anomaly_flags", response_model=AnomalyResponse)
async def get_anomaly_flags(req: AnomalyRequest, db: Session = Depends(get_db)):
    df = transactions_to_df(db)
    anomalies = detect_anomalies(df, lookback_months=req.lookback_months)
    if anomalies.empty:
        return AnomalyResponse(alerts=[])

    alerts = [
        f"{row['Date'].date()}: {row['Description']} ${abs(row['Amount']):,.0f} in {row['Category']}"
        for _, row in anomalies.head(5).iterrows()
    ]
    return AnomalyResponse(alerts=alerts)


class SavingsRequest(BaseModel):
    goal_amount: float
    goal_date: date
    starting_balance: float = 0.0


class SavingsResponse(BaseModel):
    monthly_required: float
    months_left: int


@app.post("/tools/calc_required_savings", response_model=SavingsResponse)
async def calc_required_savings(req: SavingsRequest):
    months_left = max(1, (req.goal_date.year - date.today().year) * 12 + (req.goal_date.month - date.today().month))
    gap = max(0, req.goal_amount - req.starting_balance)
    monthly_required = gap / months_left
    return SavingsResponse(monthly_required=monthly_required, months_left=months_left)


class CategorizeRequest(BaseModel):
    description: str


class CategorizeResponse(BaseModel):
    category: str
    confidence: float


@app.post("/tools/categorize_transaction", response_model=CategorizeResponse)
async def categorize_transaction(req: CategorizeRequest):
    if MODEL_PATH.exists():
        model = pd.read_pickle(MODEL_PATH)
        category = model.predict([req.description])[0]
        return CategorizeResponse(category=str(category), confidence=0.72)

    keywords = {
        "grocery": "Groceries",
        "uber": "Transport",
        "lyft": "Transport",
        "rent": "Rent",
        "mortgage": "Rent",
        "coffee": "Dining",
        "restaurant": "Dining",
        "netflix": "Subscriptions",
    }
    lowered = req.description.lower()
    for key, cat in keywords.items():
        if key in lowered:
            return CategorizeResponse(category=cat, confidence=0.35)

    return CategorizeResponse(category="Uncategorized", confidence=0.1)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("mcp_server:app", host="0.0.0.0", port=8001, reload=True)
