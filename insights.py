import pickle
from pathlib import Path
from typing import Dict, Iterable, List, Optional

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


def auto_categorize_transactions(
    df: pd.DataFrame,
    model_path: str | Path,
    feedback: Optional[Dict[str, str]] = None,
    top_n: int = 10,
):
    """
    Predict categories for uncategorized transactions using the saved classifier.

    Feedback (description -> corrected category) is applied before returning
    the ranked recommendations so the assistant "learns" user corrections.
    """

    feedback = feedback or {}
    uncategorized = df[df["Category"].isin(["Uncategorized", None, ""])]
    if uncategorized.empty:
        return pd.DataFrame()

    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
    except FileNotFoundError:
        return pd.DataFrame()

    predictions = model.predict(uncategorized["Description"].astype(str))
    probs = None
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(uncategorized["Description"].astype(str))
        labels = list(model.classes_)

    rows = []
    for idx, (_, row) in enumerate(uncategorized.iterrows()):
        desc = row["Description"]
        suggested = feedback.get(desc, predictions[idx]) if len(predictions) > idx else None
        confidence = 0.0
        if probs is not None and suggested in labels:
            label_idx = labels.index(suggested)
            confidence = float(probs[idx][label_idx])

        rows.append(
            {
                "Date": row.get("Date"),
                "Description": desc,
                "Suggested Category": suggested,
                "Confidence": confidence,
            }
        )

    ranked = pd.DataFrame(rows).sort_values("Confidence", ascending=False)
    return ranked.head(top_n)

def detect_anomalies(df, budgets: Optional[List[dict]] = None, lookback_months: int = 6):
    """Surface unusually large expenses, duplicates, and budget overrun risk."""

    if df.empty:
        return {"spikes": pd.DataFrame(), "duplicates": pd.DataFrame(), "overspend_risk": []}

    df = df.copy()
    if "Date" in df.columns:
        cutoff = df["Date"].max() - pd.DateOffset(months=lookback_months)
        df = df[df["Date"] >= cutoff]

    expenses = df[df["Amount"] < 0].copy()
    if expenses.empty:
        return {"spikes": pd.DataFrame(), "duplicates": pd.DataFrame(), "overspend_risk": []}

    std_spend = expenses["Amount"].std(ddof=0)
    if pd.isna(std_spend) or std_spend == 0:
        spike_df = pd.DataFrame()
    else:
        mean_spend = expenses["Amount"].mean()
        expenses["zscore"] = (expenses["Amount"] - mean_spend) / std_spend
        spike_df = expenses[expenses["zscore"] < -2].sort_values("zscore")

    # Duplicate detection: same merchant + amount within 7 days
    expenses["abs_amount"] = expenses["Amount"].abs()
    dup_df = (
        expenses.groupby(["Description", "abs_amount"])
        .filter(lambda g: len(g) > 1 and (g["Date"].max() - g["Date"].min()).days <= 7)
        .sort_values(["Description", "Date"])
    )

    overspend_risk = []
    if budgets:
        current_month = df["Month"].max()
        month_df = df[df["Month"] == current_month]
        day_of_month = int(month_df["Date"].max().day) if not month_df.empty else 1
        days_in_month = int(pd.Timestamp(pd.to_datetime(current_month)).days_in_month) if current_month else 30
        burn_rate = month_df[month_df["Amount"] < 0].groupby("Category")["Amount"].sum().abs()
        pace = burn_rate * (days_in_month / max(day_of_month, 1))

        for entry in budgets:
            limit = entry.get("limit", 0) or entry.get("suggested_limit", 0)
            if limit <= 0:
                continue
            projected = float(pace.get(entry["category"], 0))
            if projected > limit:
                overspend_risk.append(
                    f"{entry['category']} is pacing to ${projected:,.0f} vs ${limit:,.0f} limit. Slow discretionary spend to avoid overage."
                )

    return {"spikes": spike_df, "duplicates": dup_df, "overspend_risk": overspend_risk}

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


def build_personalized_budget(
    df: pd.DataFrame,
    savings_rate: float = 0.15,
    goal_commitments: Optional[List[dict]] = None,
):
    """Create a tailored budget based on historical averages and goal savings."""

    if df.empty:
        return {"budgets": [], "savings_target": 0.0, "income_avg": 0.0}

    monthly_income = df[df["Amount"] > 0].groupby("Month")["Amount"].sum()
    income_avg = monthly_income.mean() if not monthly_income.empty else 0.0

    category_monthly = (
        df[df["Amount"] < 0]
        .groupby(["Month", "Category"])["Amount"]
        .sum()
        .abs()
        .groupby("Category")
        .mean()
        .sort_values(ascending=False)
    )

    savings_target = income_avg * savings_rate
    if goal_commitments:
        savings_target = max(savings_target, sum(g.get("required_monthly", 0) for g in goal_commitments))

    budgets = []
    for category, avg_spend in category_monthly.items():
        # Encourage slight reduction on discretionary categories
        suggested_limit = avg_spend * 0.95 if avg_spend > 0 else 0
        budgets.append(
            {
                "category": category,
                "avg_spend": float(avg_spend),
                "suggested_limit": float(suggested_limit),
            }
        )

    return {"budgets": budgets, "savings_target": float(savings_target), "income_avg": float(income_avg)}


def track_budget_progress(df: pd.DataFrame, suggested_budgets: List[dict]):
    """Compute month-to-date spend versus suggested limits."""

    if df.empty or not suggested_budgets:
        return []

    current_month = df["Month"].max()
    month_df = df[df["Month"] == current_month]
    spend_by_cat = month_df[month_df["Amount"] < 0].groupby("Category")["Amount"].sum().abs()

    progress = []
    for budget in suggested_budgets:
        limit = budget.get("suggested_limit", 0)
        if limit <= 0:
            continue
        spent = float(spend_by_cat.get(budget["category"], 0))
        remaining = limit - spent
        pct = spent / limit if limit else 0
        progress.append(
            {
                "category": budget["category"],
                "limit": float(limit),
                "spent": float(spent),
                "remaining": float(remaining),
                "pct": pct,
                "is_over": remaining < 0,
            }
        )
    return progress


def forecast_cash_flow(
    df: pd.DataFrame,
    recurring_expenses: Optional[Iterable] = None,
    horizons: Iterable[int] = (30, 60, 90),
):
    """
    Predict cash balance over the coming horizons using recent daily net flows
    and known recurring expenses.
    """

    if df.empty:
        return []

    df_sorted = df.sort_values("Date")
    base_balance = float(df_sorted["Amount"].cumsum().iloc[-1])

    recent_window = df_sorted[df_sorted["Date"] >= df_sorted["Date"].max() - pd.Timedelta(days=90)]
    if recent_window.empty:
        recent_window = df_sorted
    daily_net = recent_window.groupby(recent_window["Date"].dt.date)["Amount"].sum().mean()

    recurring_total = 0.0
    if recurring_expenses:
        for exp in recurring_expenses:
            recurring_total += float(getattr(exp, "amount", 0) or 0)

    projections = []
    for days in horizons:
        projected_net = daily_net * days
        recurring_hit = recurring_total * (days / 30)
        ending_balance = base_balance + projected_net - recurring_hit
        projections.append(
            {
                "horizon_days": days,
                "projected_net": float(projected_net),
                "recurring": float(recurring_hit),
                "ending_balance": float(ending_balance),
            }
        )

    return projections


def goal_savings_plan(goal_name: str, target_amount: float, target_month: datetime, current_saved: float, cashflow: List[dict]):
    """Recommend a monthly savings plan aligned to projected cash flow."""

    months_remaining = max((target_month.year - datetime.today().year) * 12 + (target_month.month - datetime.today().month), 1)
    remaining_needed = max(target_amount - current_saved, 0)
    required_monthly = remaining_needed / months_remaining

    avg_surplus = 0.0
    if cashflow:
        avg_surplus = sum(p["ending_balance"] for p in cashflow) / len(cashflow)
    safe_monthly = min(required_monthly, max(avg_surplus * 0.3, required_monthly * 0.5)) if avg_surplus else required_monthly

    return {
        "goal": goal_name,
        "required_monthly": float(required_monthly),
        "safe_monthly": float(safe_monthly),
        "months_remaining": months_remaining,
        "remaining_needed": float(remaining_needed),
    }


def generate_predictive_nudges(df: pd.DataFrame, anomalies: dict, budget_progress: List[dict], cashflow: List[dict]):
    """Return concise recommendations based on anomalies, budgets, and cash runway."""

    nudges = []

    # Subscription detection: merchants charged 3+ months consecutively
    if not df.empty:
        df_sorted = df.sort_values("Date")
        monthly_counts = (
            df_sorted[df_sorted["Amount"] < 0]
            .assign(Month=lambda x: x["Date"].dt.to_period("M"))
            .groupby(["Description", "Month"])["Amount"]
            .count()
            .groupby(level=0)
            .count()
        )
        subs = monthly_counts[monthly_counts >= 3].index.tolist()
        if subs:
            nudges.append(f"🧾 Consider reviewing subscriptions: {', '.join(subs[:5])}.")

    if anomalies.get("overspend_risk"):
        nudges.extend([f"🚦 {msg}" for msg in anomalies["overspend_risk"]])

    if anomalies.get("duplicates") is not None and not anomalies["duplicates"].empty:
        dup_sample = anomalies["duplicates"].iloc[0]
        nudges.append(
            f"❗ Possible duplicate: {dup_sample['Description']} charged ${abs(dup_sample['Amount']):,.0f} twice this week."
        )

    if cashflow:
        nearest = cashflow[0]
        if nearest["ending_balance"] < 0:
            nudges.append("⚠️ Cash flow projects a shortfall this month—delay non-essential purchases or move money in.")
        else:
            nudges.append("✅ Cash flow looks positive. Automate a transfer to savings while the balance is healthy.")

    if budget_progress:
        at_risk = [b for b in budget_progress if b["pct"] >= 0.8]
        for entry in at_risk[:3]:
            nudges.append(
                f"🟠 {entry['category']} is {entry['pct']*100:.0f}% of budget. Cap spend at ${entry['remaining']*-1:,.0f} or less for the month."
            )

    return nudges

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


def assistant_response(
    df,
    query: str,
    budget_status=None,
    forecast=None,
    anomalies: Optional[dict] = None,
    cashflow: Optional[List[dict]] = None,
    goal_plan: Optional[dict] = None,
):
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

    if cashflow:
        soonest = cashflow[0]
        parts.append(
            f"Cash runway: in {soonest['horizon_days']} days you're trending to ${soonest['ending_balance']:,.0f} after recurring bills."
        )

    if budget_status:
        budget_alerts = summarize_budget_watch(budget_status)
        if budget_alerts:
            parts.append("Budget watch: " + " ".join(budget_alerts))

    if anomalies:
        if anomalies.get("spikes") is not None and not anomalies["spikes"].empty:
            top_anomaly = anomalies["spikes"].iloc[0]
            parts.append(
                f"Flagged an unusual charge on {top_anomaly['Date'].date()} for ${abs(top_anomaly['Amount']):,.0f} in {top_anomaly['Category']}."
            )
        if anomalies.get("duplicates") is not None and not anomalies["duplicates"].empty:
            dup = anomalies["duplicates"].iloc[0]
            parts.append(
                f"Possible duplicate: {dup['Description']} appears twice at ${abs(dup['Amount']):,.0f}."
            )
        if anomalies.get("overspend_risk"):
            parts.extend(anomalies["overspend_risk"])

    if goal_plan:
        parts.append(
            f"Goal '{goal_plan['goal']}': save about ${goal_plan['required_monthly']:,.0f}/mo (safe ${goal_plan['safe_monthly']:,.0f}) for {goal_plan['months_remaining']} months to hit ${goal_plan['remaining_needed']:,.0f} remaining."
        )

    if not parts:
        parts.append("I don't see any major risks right now. Keep following your plan!")

    if query:
        parts.append(f"You asked: '{query}'. Based on the data above, prioritize categories where spend is rising fastest.")

    return "\n\n".join(parts)
