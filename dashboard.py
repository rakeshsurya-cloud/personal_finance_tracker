# dashboard.py — richer dashboard with date slider + search box (client-side)

from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

def _prep(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["Amount"] = pd.to_numeric(out["Amount"])
    out["Merchant"] = out["Description"].astype(str).str.strip()
    out["Month"] = out["Date"].dt.to_period("M").dt.to_timestamp()
    out["IsExpense"] = out["Amount"] < 0
    out["AbsExpense"] = out["Amount"].where(out["Amount"] < 0, 0).abs()
    out["Income"] = out["Amount"].where(out["Amount"] > 0, 0)
    if "Category" not in out.columns:
        out["Category"] = "Uncategorized"
    return out

def _kpis(df: pd.DataFrame) -> go.Figure:
    ti = float(df["Income"].sum())
    te = float(df["AbsExpense"].sum())
    net = float(df["Amount"].sum())
    n  = int(len(df))
    fig = go.Figure()
    fig.add_trace(go.Indicator(mode="number", value=ti, number={"prefix":"$","valueformat":",.0f"},
                               title={"text":"Total Income"}, domain={"row":0,"column":0}))
    fig.add_trace(go.Indicator(mode="number", value=te, number={"prefix":"$","valueformat":",.0f"},
                               title={"text":"Total Expenses"}, domain={"row":0,"column":1}))
    fig.add_trace(go.Indicator(mode="number", value=net, number={"prefix":"$","valueformat":",.0f"},
                               title={"text":"Net Cash Flow"}, domain={"row":0,"column":2}))
    fig.add_trace(go.Indicator(mode="number", value=n, title={"text":"Transactions"},
                               domain={"row":0,"column":3}))
    fig.update_layout(grid={"rows":1,"columns":4}, height=180, margin=dict(l=20,r=20,t=20,b=10))
    return fig

def cat_spend(df: pd.DataFrame) -> go.Figure:
    by_cat = (df.loc[df["IsExpense"]]
                .groupby("Category", as_index=False)["AbsExpense"].sum()
                .sort_values("AbsExpense", ascending=False))
    fig = px.bar(by_cat, x="Category", y="AbsExpense", title="Spending by Category (Expenses)")
    fig.update_layout(yaxis_title="Total Spent", xaxis_title="Category", height=380,
                      margin=dict(l=40,r=20,t=60,b=40))
    # Legend note: click category bars in legend to isolate/hide series
    return fig

def income_vs_expense_monthly(df: pd.DataFrame) -> go.Figure:
    by_m = df.groupby("Month", as_index=False).agg(Income=("Income","sum"), Expenses=("AbsExpense","sum"))
    fig = go.Figure()
    fig.add_bar(x=by_m["Month"], y=by_m["Income"], name="Income")
    fig.add_bar(x=by_m["Month"], y=by_m["Expenses"], name="Expenses")
    fig.update_layout(barmode="group", title="Income vs. Expenses by Month",
                      xaxis_title="Month", yaxis_title="Amount", height=380,
                      margin=dict(l=40,r=20,t=60,b=40))
    # Date range slider
    fig.update_xaxes(rangeslider=dict(visible=True))
    return fig

def net_cashflow_month(df: pd.DataFrame) -> go.Figure:
    by_m = df.groupby("Month", as_index=False)["Amount"].sum()
    fig = px.line(by_m, x="Month", y="Amount", title="Net Cash Flow by Month")
    fig.update_layout(yaxis_title="Net", xaxis_title="Month", height=320, margin=dict(l=40,r=20,t=60,b=40))
    fig.update_xaxes(rangeslider=dict(visible=True))
    return fig

def top_merchants(df: pd.DataFrame, days:int=90, top_k:int=10) -> go.Figure:
    cutoff = df["Date"].max() - pd.Timedelta(days=days) if not df.empty else pd.Timestamp.utcnow() - pd.Timedelta(days=days)
    recent = df[(df["Date"] >= cutoff) & (df["IsExpense"])]
    by_m = (recent.groupby("Merchant", as_index=False)["AbsExpense"].sum()
                 .sort_values("AbsExpense", ascending=False).head(top_k))
    fig = px.bar(by_m, x="Merchant", y="AbsExpense", title=f"Top Merchants (last {days} days)")
    fig.update_layout(yaxis_title="Total Spent", xaxis_title="", height=380, margin=dict(l=40,r=20,t=60,b=120))
    fig.update_xaxes(tickangle=30)
    return fig

def recurring_vs_onetime(df: pd.DataFrame) -> go.Figure:
    counts = (df[df["IsExpense"]]
              .groupby("Merchant")
              .agg(n_months=("Month","nunique"), total=("AbsExpense","sum"))
              .reset_index())
    counts["Type"] = counts["n_months"].apply(lambda n: "Recurring" if n >= 3 else "One-time")
    by_type = counts.groupby("Type", as_index=False)["total"].sum()
    fig = px.pie(by_type, names="Type", values="total", title="Recurring vs. One-time (by spend)")
    fig.update_layout(height=340, margin=dict(l=20,r=20,t=60,b=20))
    return fig

def recent_table_html(df: pd.DataFrame, n:int=100) -> str:
    # Plain HTML table for client-side search
    tbl = df.sort_values("Date", ascending=False).head(n)[["Date","Description","Category","Amount"]].copy()
    # format date/amount
    tbl["Date"] = pd.to_datetime(tbl["Date"]).dt.date.astype(str)
    tbl["Amount"] = tbl["Amount"].map(lambda x: f"${x:,.2f}")
    head = "<table id='recentTable' style='width:100%;border-collapse:collapse;font-family:system-ui'>"
    thead = "<thead><tr>" + "".join(f"<th style='text-align:left;border-bottom:1px solid #ddd;padding:6px'>{c}</th>" for c in tbl.columns) + "</tr></thead>"
    rows = []
    for _, r in tbl.iterrows():
        tds = "".join(f"<td style='padding:6px;border-bottom:1px solid #f0f0f0'>{r[c]}</td>" for c in tbl.columns)
        rows.append(f"<tr>{tds}</tr>")
    tbody = "<tbody>" + "".join(rows) + "</tbody>"
    tail = "</table>"
    # Simple search box JS
    search = """
    <input id="searchBox" placeholder="Search Description..." style="margin:8px 0;padding:6px;width:50%;font-family:system-ui"/>
    <script>
      const box = document.getElementById('searchBox');
      const tbl = document.getElementById('recentTable').getElementsByTagName('tbody')[0];
      box.addEventListener('input', () => {
        const q = box.value.toLowerCase();
        for (const row of tbl.rows) {
          const desc = row.cells[1].innerText.toLowerCase();
          row.style.display = desc.includes(q) ? '' : 'none';
        }
      });
    </script>
    """
    return search + head + thead + tbody + tail

def build_dashboard(categorized_csv: str | Path, out_html: str | Path) -> None:
    df = pd.read_csv(categorized_csv)
    df = _prep(df)

    sections = [
        ("KPIs", _kpis(df)),
        ("Spending by Category", cat_spend(df)),
        ("Income vs. Expenses", income_vs_expense_monthly(df)),
        ("Net Cash Flow", net_cashflow_month(df)),
        ("Top Merchants", top_merchants(df)),
        ("Recurring vs One-time", recurring_vs_onetime(df)),
    ]

    html_parts = [
        "<html><head><meta charset='utf-8'><title>Personal Finance Dashboard</title></head><body>",
        "<h1 style='font-family:system-ui;margin:12px 16px'>Personal Finance Dashboard</h1>",
        "<p style='font-family:system-ui;margin:0 16px 12px'>Tip: use the legend to isolate a category; drag or use the range slider on time charts; use the search box below to filter recent transactions.</p>"
    ]
    for title, fig in sections:
        html_parts.append(f"<h2 style='font-family:system-ui;margin:12px 16px 0'>{title}</h2>")
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs='cdn'))

    # Recent transactions with client-side search
    html_parts.append("<h2 style='font-family:system-ui;margin:12px 16px 0'>Recent Transactions</h2>")
    html_parts.append(recent_table_html(df, n=250))

    html_parts.append("</body></html>")
    Path(out_html).write_text("\n".join(html_parts), encoding="utf-8")

# Backward-compat wrapper
def generate_dashboard(categorized_csv: str, out_html: str) -> None:
    build_dashboard(categorized_csv, out_html)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    build_dashboard(args.csv, args.out)
