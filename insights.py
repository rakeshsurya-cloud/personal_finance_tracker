import pickle
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
from datetime import datetime, timedelta


def compute_highlights(df):
    """Summarize the latest month of data for quick highlights."""

    if df.empty:
        return {}

    latest_month = df["Month"].max()
    month_df = df[df["Month"] == latest_month]

    income = month_df[month_df["Amount"] > 0]["Amount"].sum()
    expenses = month_df[month_df["Amount"] < 0]["Amount"].sum()
    net_cashflow = income + expenses

    expense_rows = month_df[month_df["Amount"] < 0]
    top_category = None
    top_category_spend = 0
    if not expense_rows.empty:
        by_cat = expense_rows.groupby("Category")["Amount"].sum().abs().sort_values(ascending=False)
        if not by_cat.empty:
            top_category = by_cat.index[0]
            top_category_spend = by_cat.iloc[0]

    return {
        "month": latest_month,
        "income": float(income),
        "spend": float(abs(expenses)),
        "net": float(net_cashflow),
        "top_category": top_category,
        "top_category_spend": float(top_category_spend),
        "avg_ticket": float(abs(expense_rows["Amount"].mean())) if not expense_rows.empty else 0.0,
    }

def detect_anomalies(df, lookback_months: int = 6):
    """Surface unusually large expenses using a z-score over recent data."""

    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    if "Date" in df.columns:
        cutoff = df["Date"].max() - pd.DateOffset(months=lookback_months)
        df = df[df["Date"] >= cutoff]

    expenses = df[df["Amount"] < 0].copy()
    if expenses.empty:
        return pd.DataFrame()

    std_spend = expenses["Amount"].std(ddof=0)
    if pd.isna(std_spend) or std_spend == 0:
        return pd.DataFrame()

    mean_spend = expenses["Amount"].mean()
    expenses["zscore"] = (expenses["Amount"] - mean_spend) / std_spend
    anomalies = expenses[expenses["zscore"] < -2].sort_values("zscore")
    return anomalies

def predict_spending(df):
    """Rolling-average + trend forecast for next month's spending."""

    import plotly.express as px

    monthly = (
        df[df["Amount"] < 0]
        .groupby("Month")["Amount"]
        .sum()
        .abs()
        .reset_index()
        .sort_values("Month")
    )

    if len(monthly) < 2:
        return {
            "figure": px.line(title="Not enough data to predict"),
            "summary": "Add a second month of expenses to unlock forecasting.",
            "forecast_month": None,
            "forecast_value": None,
            "updated_at": datetime.utcnow(),
        }

    lookback = min(3, len(monthly))
    monthly["rolling_avg"] = monthly["Amount"].rolling(window=lookback, min_periods=2).mean()
    monthly["trend"] = monthly["Amount"].diff()
    recent_trend = monthly["trend"].tail(lookback).mean()

    rolling_forecast = monthly["rolling_avg"].iloc[-1]
    trend_adjusted = max(monthly["Amount"].iloc[-1] + (recent_trend if pd.notna(recent_trend) else 0), 0)
    forecast_value = (0.6 * rolling_forecast) + (0.4 * trend_adjusted)

    last_month = monthly["Month"].max()
    try:
        next_month_date = pd.to_datetime(last_month) + pd.DateOffset(months=1)
        next_month = next_month_date.strftime("%Y-%m")
    except Exception:
        next_month = "Next Month"

    forecast = pd.DataFrame({
        "Month": [next_month],
        "Amount": [forecast_value],
        "Type": ["Forecast"],
    })

    monthly["Type"] = "Actual"
    combined = pd.concat([monthly, forecast])

    fig = px.line(
        combined,
        x="Month",
        y="Amount",
        color="Type",
        markers=True,
        title="Spending Forecast",
    )

    summary = (
        f"Using a {lookback}-month rolling average with recent trend signals, next month is "
        f"projected around ${forecast_value:,.0f}."
    )

    return {
        "figure": fig,
        "summary": summary,
        "forecast_month": next_month,
        "forecast_value": float(forecast_value),
        "updated_at": datetime.utcnow(),
    }

def generate_actionable_tips(
    df: pd.DataFrame,
    budget_status=None,
    anomalies: Optional[pd.DataFrame] = None,
    forecast: Optional[Dict] = None,
    fixed_expenses_total: float = 0.0,
    window_label: Optional[str] = None,
):
    """Generates richer, timeframe-aware financial tips."""
    tips = []

    if df.empty:
        return tips

    current_month = df["Month"].max()
    month_df = df[df["Month"] == current_month]

    # 1. Spending Spikes & pacing vs last month
    try:
        last_month = (pd.to_datetime(current_month) - pd.DateOffset(months=1)).strftime("%Y-%m")
    except Exception:
        last_month = None

    if last_month:
        curr_spend = month_df[month_df["Amount"] < 0]["Amount"].sum()
        last_spend = df[(df["Month"] == last_month) & (df["Amount"] < 0)]["Amount"].sum()
        if abs(curr_spend) > abs(last_spend) * 1.2:
            tips.append(
                "⚠️ **Spending Alert**: You're pacing 20%+ higher than last month. Hold discretionary spend for a week and review big-ticket items."
            )

    # 2. High Category Spend vs history
    cat_spend = month_df.groupby("Category")["Amount"].sum().sort_values()
    if not cat_spend.empty:
        top_cat = cat_spend.index[0]
        top_val = abs(cat_spend.iloc[0])
        trailing = (
            df[df["Month"] != current_month]
            .groupby("Category")["Amount"]
            .mean()
            .abs()
        )
        trailing_avg = trailing.get(top_cat, 0)
        if trailing_avg > 0 and top_val > trailing_avg * 1.3:
            tips.append(
                f"📈 **{top_cat} is trending hot**: ${top_val:,.0f} vs typical ${trailing_avg:,.0f}. Set a cap for the next 7 days."
            )
        else:
            tips.append(
                f"🍔 **Top Category**: ${top_val:,.0f} spent on **{top_cat}** this month. Shift one purchase to savings to stay on track."
            )

    # 3. Budget risks
    for entry in budget_status or []:
        if entry["limit"] <= 0:
            continue
        pct = entry["pct"]
        if entry["is_over"]:
            tips.append(
                f"🔴 **Budget overrun**: {entry['category']} is over by ${abs(entry['remaining']):,.0f}. Pause spending here for the rest of {window_label or 'the month'}."
            )
        elif pct >= 0.8:
            tips.append(
                f"🟠 **At risk**: {entry['category']} is {pct*100:.0f}% of its ${entry['limit']:,.0f} limit. Reduce by ${max(0, entry['spent'] - entry['limit']*0.8):,.0f} this week."
            )

    # 4. Anomalies & duplicates
    if anomalies is not None and not anomalies.empty:
        spike = anomalies.iloc[0]
        tips.append(
            f"🚨 **Unusual charge**: {spike['Description']} on {spike['Date'].date()} for ${abs(spike['Amount']):,.0f}. Verify this transaction."
        )

    dupes = (
        month_df[month_df["Amount"] < 0]
        .groupby(["Description", "Amount"])
        .filter(lambda g: len(g) >= 2)
        .drop_duplicates(subset=["Description", "Amount"])
    )
    if not dupes.empty:
        d = dupes.iloc[0]
        tips.append(
            f"🧐 **Possible duplicate**: '{d['Description']}' appears multiple times for ${abs(d['Amount']):,.2f}. Check if this is a repeat charge."
        )

    # 5. Savings rate / runway
    income = month_df[month_df["Amount"] > 0]["Amount"].sum()
    spend = abs(month_df[month_df["Amount"] < 0]["Amount"].sum())
    if income > 0:
        savings_rate = (income - spend) / income
        if savings_rate < 0.2:
            tips.append(
                f"💸 **Savings gap**: Savings rate is {savings_rate*100:.0f}% (target 20%). Trim discretionary spend by ${max(0, spend - income*0.8):,.0f} to close the gap."
            )

    if forecast and forecast.get("forecast_value") and income > 0:
        projected_spend = forecast["forecast_value"]
        if projected_spend > income:
            tips.append(
                f"⏳ **Cash runway risk**: Forecast spend (${projected_spend:,.0f}) exceeds typical income (${income:,.0f}). Lock discretionary categories and pre-schedule transfers to savings."
            )

    # 6. Fixed expense coverage
    if fixed_expenses_total > 0 and income > 0:
        coverage = income - fixed_expenses_total
        if coverage < 0:
            tips.append(
                f"🏠 **Fixed bills exceed income** by ${abs(coverage):,.0f}. Consider renegotiating bills or boosting income immediately."
            )

    return tips


def summarize_budget_watch(budget_status):
    """Return human-readable budget alerts for overspend and at-risk categories."""

    alerts = []
    for entry in budget_status or []:
        if entry["limit"] <= 0:
            continue

        pct = entry["pct"]
        if entry["is_over"]:
            alerts.append(
                f"🔴 **{entry['category']}** is over budget by ${abs(entry['remaining']):,.0f} (spent ${entry['spent']:,.0f} of ${entry['limit']:,.0f})."
            )
        elif pct >= 0.8:
            alerts.append(
                f"🟠 **{entry['category']}** is {pct*100:.0f}% of its ${entry['limit']:,.0f} limit. Slow down to avoid overruns."
            )
    return alerts


def assistant_response(
    df: pd.DataFrame,
    query: str,
    budget_status=None,
    forecast=None,
    anomalies=None,
    tips: Optional[List[str]] = None,
    window_label: Optional[str] = None,
):
    """Question-aware assistant that cites the most relevant data points."""

    highlights = compute_highlights(df)
    parts = []

    if highlights:
        parts.append(
            f"For {highlights['month']}, income is ${highlights['income']:,.0f} and spending is ${highlights['spend']:,.0f}, leaving a net of ${highlights['net']:,.0f}."
        )

    if forecast and forecast.get("forecast_value"):
        parts.append(
            f"Next month is projected around ${forecast['forecast_value']:,.0f} based on recent trends."
        )

    if budget_status:
        budget_alerts = summarize_budget_watch(budget_status)
        if budget_alerts:
            parts.append("Budget watch: " + " ".join(budget_alerts))

    if anomalies is not None and not anomalies.empty:
        top_anomaly = anomalies.iloc[0]
        parts.append(
            f"Flagged an unusual charge on {top_anomaly['Date'].date()} for ${abs(top_anomaly['Amount']):,.0f} in {top_anomaly['Category']}."
        )

    # Intent-aware follow ups
    lower_q = (query or "").lower()
    if "subscription" in lower_q or "recurring" in lower_q:
        recurring = df[df["Description"].str.contains("subscr|auto|recurring", case=False, na=False)]
        if not recurring.empty:
            total_recurring = recurring[recurring["Amount"] < 0]["Amount"].sum()
            parts.append(
                f"Recurring-like charges this window: ${abs(total_recurring):,.0f} across {recurring['Description'].nunique()} merchants."
            )
    if "savings" in lower_q or "runway" in lower_q:
        income = df[df["Amount"] > 0]["Amount"].sum()
        spend = abs(df[df["Amount"] < 0]["Amount"].sum())
        if income > 0:
            rate = (income - spend) / income
            parts.append(f"Savings rate for {window_label or 'this window'} is {rate*100:.1f}%.")
    if "debt" in lower_q or "loan" in lower_q:
        parts.append("For debt payoff, use avalanche ordering and redirect any surplus above fixed bills to the highest APR loan.")

    if tips:
        parts.append("Next steps: " + " ".join(tips[:3]))

    if not parts:
        parts.append("I don't see any major risks right now. Keep following your plan!")

    return "\n\n".join(parts)
WINDOW_LABELS = ["Last 90 days", "Last 180 days", "Year to date", "All data"]


def filter_by_timeframe(df: pd.DataFrame, window_label: str) -> Tuple[pd.DataFrame, Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]]:
    """Return a dataframe filtered by the requested timeframe plus bounds for downstream metrics."""

    if df.empty:
        return df, (None, None)

    window_df = df.copy()
    start = None
    end = window_df["Date"].max()

    if window_label == "Last 90 days":
        start = end - pd.Timedelta(days=90)
    elif window_label == "Last 180 days":
        start = end - pd.Timedelta(days=180)
    elif window_label == "Year to date":
        start = pd.Timestamp(pd.Timestamp.today().year, 1, 1)

    if start is not None:
        window_df = window_df[window_df["Date"] >= start]

    return window_df, (start, end)
