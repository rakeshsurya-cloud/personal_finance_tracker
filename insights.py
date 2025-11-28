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

def generate_actionable_tips(df):
    """
    Generates rule-based financial tips.
    """
    tips = []
    
    if df.empty:
        return tips

    # 1. Spending Spikes
    current_month = df["Month"].max()
    try:
        last_month = (pd.to_datetime(current_month) - pd.DateOffset(months=1)).strftime("%Y-%m")
    except Exception:
        last_month = None

    if last_month:
        curr_spend = df[(df["Month"] == current_month) & (df["Amount"] < 0)]["Amount"].sum()
        last_spend = df[(df["Month"] == last_month) & (df["Amount"] < 0)]["Amount"].sum()

        if abs(curr_spend) > abs(last_spend) * 1.2:
            tips.append(
                "⚠️ **Spending Alert**: You're pacing 20% higher than last month. Consider pausing discretionary spend this week."
            )

    # 2. High Category Spend
    cat_spend = df[df["Month"] == current_month].groupby("Category")["Amount"].sum().sort_values()
    if not cat_spend.empty:
        top_cat = cat_spend.index[0]  # Most negative
        top_val = abs(cat_spend.iloc[0])
        tips.append(
            f"🍔 **Top Category**: ${top_val:,.0f} spent on **{top_cat}** this month. Shift a single purchase to savings to stay on track."
        )

    # 3. Savings Opportunity
    income = df[df["Month"] == current_month][df["Amount"] > 0]["Amount"].sum()
    curr_spend = df[(df["Month"] == current_month) & (df["Amount"] < 0)]["Amount"].sum()

    if income > 0 and (abs(curr_spend) / income) < 0.5:
        tips.append(
            "💰 **Great Job**: You've saved 50%+ of income this month. Move the surplus to your emergency fund or investments."
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


def assistant_response(df, query: str, budget_status=None, forecast=None, anomalies=None):
    """Rule-based assistant that tailors a response to the provided question."""

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

    if not parts:
        parts.append("I don't see any major risks right now. Keep following your plan!")

    if query:
        parts.append(f"You asked: '{query}'. Based on the data above, prioritize categories where spend is rising fastest.")

    return "\n\n".join(parts)
