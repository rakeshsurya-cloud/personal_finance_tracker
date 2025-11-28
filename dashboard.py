# dashboard.py — richer dashboard with date slider + search box (client-side)

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from typing import Optional, Tuple

def _prep(df):
    """
    Prepares the dataframe for dashboarding.
    """
    if df.empty:
        return df
    
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    
    # Ensure Amount is numeric
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    
    # Helper columns
    df['IsExpense'] = df['Amount'] < 0
    df['AbsExpense'] = df['Amount'].where(df['Amount'] < 0, 0).abs()
    df['Income'] = df['Amount'].where(df['Amount'] > 0, 0)
    
    if "Category" not in df.columns:
        df["Category"] = "Uncategorized"
    else:
        df["Category"] = df["Category"].fillna("Uncategorized").replace("", "Uncategorized")
        
    return df

def _kpis(
    df: pd.DataFrame,
    fixed_expenses_total: float = 0.0,
    window_bounds: Optional[Tuple[pd.Timestamp, pd.Timestamp]] = None,
    window_label: Optional[str] = None,
):
    """
    Displays the top-level KPIs with 'Wow' factor.

    The metrics align with the selected analysis window and fall back to
    the most recent month that has transactions (instead of assuming the
    current calendar month always has data).
    """
    df_curr = df.copy()
    if window_bounds:
        start, end = window_bounds
        if start is not None:
            df_curr = df_curr[df_curr["Date"] >= start]
        if end is not None:
            df_curr = df_curr[df_curr["Date"] <= end]

    if df_curr.empty:
        st.info("No data available for the selected window.")
        return

    # Target the latest month that exists in the filtered data
    latest_month = df_curr["Month"].max()
    df_curr = df_curr[df_curr["Month"] == latest_month]

    # 1. Total Income (Positive transactions, excluding transfers/payments)
    income = df_curr[(df_curr['Amount'] > 0) & (~df_curr['Category'].isin(['Transfer', 'Payment']))]['Amount'].sum()

    # 2. Total Spend (Negative transactions, excluding transfers/payments)
    spend = abs(df_curr[(df_curr['Amount'] < 0) & (~df_curr['Category'].isin(['Transfer', 'Payment']))]['Amount'].sum())

    # 3. Net Cashflow
    net = income - spend

    # 4. Savings Rate (guard against division by zero)
    savings_rate = (net / income * 100) if income > 0 else 0.0

    # 5. Safe to Spend avoids double-counting fixed expenses
    savings_goal = income * 0.20
    discretionary_spend = max(spend - fixed_expenses_total, 0)
    safe_to_spend = income - fixed_expenses_total - savings_goal - discretionary_spend

    col1, col2, col3, col4 = st.columns(4)

    label_suffix = f" ({window_label})" if window_label else ""
    col1.metric(f"💰 Income{label_suffix}", f"${income:,.0f}", delta_color="normal")
    col2.metric(f"💸 Spent{label_suffix}", f"${spend:,.0f}", delta=f"-${spend:,.0f}", delta_color="inverse")
    col3.metric("📉 Savings Rate", f"{savings_rate:.1f}%", delta="Target: 20%")
    col4.metric(
        "🛡️ Safe to Spend",
        f"${max(0, safe_to_spend):,.0f}",
        help="Income - fixed bills - 20% savings goal - discretionary spend in this window.",
    )

    # Progress Bar for Budget (Simple 50/30/20 rule visualization)
    st.caption("Monthly Budget Progress")
    progress = min(1.0, spend / income) if income > 0 else 0
    st.progress(progress)


def income_vs_expense_monthly(df):
    """
    Bar chart of Income vs Expenses per month.
    """
    # Group by Month and Type (Pos/Neg)
    monthly = df.groupby('Month')['Amount'].agg(
        Income=lambda x: x[x > 0].sum(),
        Expense=lambda x: abs(x[x < 0].sum())
    ).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly['Month'], y=monthly['Income'], name='Income', marker_color='#4CAF50'))
    fig.add_trace(go.Bar(x=monthly['Month'], y=monthly['Expense'], name='Expenses', marker_color='#FF5252'))
    
    fig.update_layout(barmode='group', title="Income vs Expenses Trend", height=400)
    return fig

def cat_spend(df):
    """
    Donut chart of spending by category (excluding Income/Transfers).
    """
    # Filter out income and transfers
    spend_df = df[(df['Amount'] < 0) & (~df['Category'].isin(['Transfer', 'Payment', 'Income']))].copy()
    spend_df['Category'] = spend_df['Category'].fillna('Uncategorized').replace('', 'Uncategorized')
    spend_df['Amount'] = abs(spend_df['Amount'])
    
    by_cat = spend_df.groupby('Category')['Amount'].sum().reset_index()
    
    fig = px.pie(by_cat, values='Amount', names='Category', hole=0.4, title="Spending by Category")
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def net_worth_trend(df):
    """
    Area chart of Net Worth (Cumulative Cashflow) over time.
    """
    # Calculate daily net change
    daily = df.groupby('Date')['Amount'].sum().cumsum().reset_index()
    daily.rename(columns={'Amount': 'Net Worth'}, inplace=True)
    
    fig = px.area(daily, x='Date', y='Net Worth', title="Net Worth Growth (Cash Assets)")
    fig.update_layout(height=350)
    return fig

