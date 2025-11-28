import pandas as pd
from datetime import datetime, timedelta

def detect_anomalies(df):
    """
    Detects transactions that are > 2 std dev from the mean.
    """
    if df.empty:
        return pd.DataFrame()
        
    df = df.copy()
    mean_spend = df[df['Amount'] < 0]['Amount'].mean()
    std_spend = df[df['Amount'] < 0]['Amount'].std()
    
    # Anomaly = Amount < (Mean - 2*Std) (since expenses are negative)
    threshold = mean_spend - (2 * std_spend)
    
    anomalies = df[df['Amount'] < threshold]
    return anomalies

def predict_spending(df):
    """
    Simple linear forecast for next month's spending.
    """
    import plotly.express as px
    
    # Group by month
    monthly = df[df['Amount'] < 0].groupby('Month')['Amount'].sum().reset_index()
    monthly['Amount'] = abs(monthly['Amount'])
    
    if len(monthly) < 2:
        return px.line(title="Not enough data to predict")
        
    # Simple average of last 3 months
    avg_spend = monthly['Amount'].tail(3).mean()
    
    # Create forecast data
    last_month = monthly['Month'].max()
    # Handle string or timestamp
    try:
        next_month_date = pd.to_datetime(last_month) + pd.DateOffset(months=1)
        next_month = next_month_date.strftime("%Y-%m")
    except:
        next_month = "Next Month"
        
    forecast = pd.DataFrame({
        'Month': [next_month],
        'Amount': [avg_spend],
        'Type': ['Forecast']
    })
    
    monthly['Type'] = 'Actual'
    combined = pd.concat([monthly, forecast])
    
    fig = px.line(combined, x='Month', y='Amount', color='Type', markers=True, title="Spending Forecast")
    return fig

def generate_actionable_tips(df):
    """
    Generates rule-based financial tips.
    """
    tips = []
    
    if df.empty:
        return tips
        
    # 1. Spending Spikes
    current_month = df['Month'].max()
    # Calculate last month safely
    try:
        last_month = (pd.to_datetime(current_month) - pd.DateOffset(months=1)).strftime("%Y-%m")
    except:
        last_month = None
    
    if last_month:
        curr_spend = df[(df['Month'] == current_month) & (df['Amount'] < 0)]['Amount'].sum()
        last_spend = df[(df['Month'] == last_month) & (df['Amount'] < 0)]['Amount'].sum()
        
        if abs(curr_spend) > abs(last_spend) * 1.2:
            tips.append(f"⚠️ **Spending Alert**: You've spent 20% more this month compared to last month.")
        
    # 2. High Category Spend
    cat_spend = df[df['Month'] == current_month].groupby('Category')['Amount'].sum().sort_values()
    if not cat_spend.empty:
        top_cat = cat_spend.index[0] # Most negative
        top_val = abs(cat_spend.iloc[0])
        tips.append(f"🍔 **Top Category**: You spent ${top_val:,.0f} on **{top_cat}** this month. Can you cut this by 10%?")
        
    # 3. Savings Opportunity
    income = df[df['Month'] == current_month][df['Amount'] > 0]['Amount'].sum()
    curr_spend = df[(df['Month'] == current_month) & (df['Amount'] < 0)]['Amount'].sum()
    
    if income > 0 and (abs(curr_spend) / income) < 0.5:
        tips.append(f"💰 **Great Job**: You've saved more than 50% of your income this month! Consider investing the surplus.")
        
    return tips
