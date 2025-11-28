# dashboard.py — richer dashboard with date slider + search box (client-side)

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date

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
        
    return df

def _kpis(df, fixed_expenses_total=0.0):
    """
    Displays the top-level KPIs with 'Wow' factor.
    """
    # Filter for current month
    current_month = str(date.today().strftime("%Y-%m"))
    df_curr = df[df['Month'] == current_month]
    
    # 1. Total Income (Positive transactions, excluding transfers)
    income = df_curr[df_curr['Amount'] > 0]['Amount'].sum()
    
    # 2. Total Spend (Negative transactions, excluding transfers)
    spend = abs(df_curr[df_curr['Amount'] < 0]['Amount'].sum())
    
    # 3. Net Cashflow
    net = income - spend
    
    # 4. Savings Rate
    savings_rate = (net / income * 100) if income > 0 else 0.0
    
    # 5. Safe to Spend
    # (Income - Fixed Expenses - Savings Goal (20% default))
    savings_goal = income * 0.20
    safe_to_spend = income - fixed_expenses_total - savings_goal - (spend - fixed_expenses_total) 
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("💰 Income (This Month)", f"${income:,.0f}", delta_color="normal")
    col2.metric("💸 Spent (This Month)", f"${spend:,.0f}", delta=f"-${spend:,.0f}", delta_color="inverse")
    col3.metric("📉 Savings Rate", f"{savings_rate:.1f}%", delta="Target: 20%")
    col4.metric("🛡️ Safe to Spend", f"${max(0, safe_to_spend):,.0f}", help="Income - Fixed Bills - 20% Savings - Already Spent")

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

