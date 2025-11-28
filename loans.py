from __future__ import annotations
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import math

def _prep_loans(loans: pd.DataFrame) -> pd.DataFrame:
    df = loans.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    for col in ["Principal","InterestRateAPR","TermMonths","PaymentAmount","Balance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["LoanType"] = df["LoanType"].fillna("Other").str.title()
    # Sanity: effective monthly rate
    df["RateMonthly"] = (df["InterestRateAPR"]/100.0)/12.0
    # Simple rough remaining months if PaymentAmount > interest-only
    def est_remaining_months(r, bal, pmt):
        if pmt <= r*bal or pmt <= 0 or bal <= 0: return None
        try:
            n = -math.log(1 - r*bal/pmt) / math.log(1+r)
            return max(0, n)
        except Exception:
            return None
    df["EstMonthsLeft"] = df.apply(lambda r: est_remaining_months(r["RateMonthly"], r["Balance"], r["PaymentAmount"]), axis=1)
    return df

def simulate_payoff(balance: float, rate_apr: float, monthly_payment: float, extra_payment: float = 0) -> pd.DataFrame:
    """
    Simulates the amortization schedule of a loan.
    Returns a DataFrame with Month, Balance, Interest, Principal.
    """
    if balance <= 0 or monthly_payment <= 0:
        return pd.DataFrame()
    
    monthly_rate = (rate_apr / 100.0) / 12.0
    total_payment = monthly_payment + extra_payment
    
    # If payment is too low to cover interest, it will never pay off
    if total_payment <= balance * monthly_rate:
        return pd.DataFrame() # Infinite loop prevention

    schedule = []
    curr_balance = balance
    month = 0
    
    while curr_balance > 0 and month < 1200: # Cap at 100 years
        month += 1
        interest = curr_balance * monthly_rate
        principal = total_payment - interest
        
        if principal > curr_balance:
            principal = curr_balance
            total_payment = interest + principal
            
        curr_balance -= principal
        schedule.append({
            "Month": month,
            "Balance": max(0, curr_balance),
            "Interest": interest,
            "Principal": principal,
            "TotalPayment": total_payment
        })
        
    return pd.DataFrame(schedule)


