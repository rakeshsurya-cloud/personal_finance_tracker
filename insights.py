import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go
import plotly.express as px

def detect_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    """
    Uses Isolation Forest to detect anomalous transactions based on Amount.
    Returns the DataFrame with an 'IsAnomaly' column.
    """
    if df.empty or len(df) < 10:
        return df
    
    # Prepare data: Use Amount (absolute) for anomaly detection
    # We focus on expenses for anomalies usually
    expenses = df[df["Amount"] < 0].copy()
    if expenses.empty:
        return df
        
    X = expenses[["Amount"]].abs().values.reshape(-1, 1)
    
    model = IsolationForest(contamination=contamination, random_state=42)
    expenses["AnomalyScore"] = model.fit_predict(X)
    
    # -1 is anomaly, 1 is normal
    anomalies = expenses[expenses["AnomalyScore"] == -1]
    
    # Merge back to original df
    df["IsAnomaly"] = False
    df.loc[anomalies.index, "IsAnomaly"] = True
    
    return df

def predict_spending(df: pd.DataFrame) -> go.Figure:
    """
    Forecasts next month's total spending using simple Linear Regression on monthly totals.
    """
    if df.empty:
        return go.Figure()
        
    # Aggregate by month
    df["Date"] = pd.to_datetime(df["Date"])
    monthly = df[df["Amount"] < 0].copy()
    monthly["Month"] = monthly["Date"].dt.to_period("M").dt.to_timestamp()
    monthly_spend = monthly.groupby("Month")["Amount"].sum().abs().reset_index()
    
    if len(monthly_spend) < 3:
        return go.Figure().add_annotation(text="Need at least 3 months of data to forecast.", showarrow=False)
        
    # Prepare for regression
    monthly_spend["MonthOrdinal"] = monthly_spend["Month"].map(pd.Timestamp.toordinal)
    X = monthly_spend[["MonthOrdinal"]]
    y = monthly_spend["Amount"]
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict next month
    last_month = monthly_spend["Month"].max()
    next_month = last_month + pd.DateOffset(months=1)
    next_month_ordinal = np.array([[next_month.toordinal()]])
    prediction = model.predict(next_month_ordinal)[0]
    
    # Plot
    fig = px.line(monthly_spend, x="Month", y="Amount", title="Monthly Spending Trend & Forecast", markers=True)
    fig.add_scatter(x=[next_month], y=[prediction], mode="markers+text", name="Forecast", 
                    text=[f"${prediction:,.0f}"], textposition="top center",
                    marker=dict(color="red", size=12, symbol="star"))
    
    fig.update_layout(yaxis_title="Total Spending", xaxis_title="Month")
    return fig
