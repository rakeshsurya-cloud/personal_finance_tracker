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

def build_loans_dashboard(loans_csv: str | Path, out_html: str | Path) -> None:
    loans = pd.read_csv(loans_csv)
    df = _prep_loans(loans)

    # Tiles by type
    by_type_bal = df.groupby("LoanType", as_index=False)["Balance"].sum().sort_values("Balance", ascending=False)
    by_type_prin = df.groupby("LoanType", as_index=False)["Principal"].sum()

    tiles = go.Figure()
    total_bal = float(df["Balance"].sum())
    total_pmt = float(df["PaymentAmount"].sum())
    tiles.add_trace(go.Indicator(mode="number", value=total_bal, number={"prefix":"$","valueformat":",.0f"},
                                 title={"text":"Total Outstanding"}, domain={"row":0,"column":0}))
    tiles.add_trace(go.Indicator(mode="number", value=total_pmt, number={"prefix":"$","valueformat":",.0f"},
                                 title={"text":"Monthly Payments"}, domain={"row":0,"column":1}))
    tiles.update_layout(grid={"rows":1,"columns":2}, height=140, margin=dict(l=20,r=20,t=20,b=10))

    # Breakdown charts
    fig_bal = px.bar(by_type_bal, x="LoanType", y="Balance", title="Outstanding Balance by Loan Type")
    fig_bal.update_layout(yaxis_title="Balance", xaxis_title="Loan Type", height=360, margin=dict(l=40,r=20,t=60,b=40))

    fig_prin = px.bar(by_type_prin, x="LoanType", y="Principal", title="Original Principal by Loan Type")
    fig_prin.update_layout(yaxis_title="Principal", xaxis_title="Loan Type", height=360, margin=dict(l=40,r=20,t=60,b=40))

    # Table (sortable via the browser’s built-in sort if desired)
    show = df.copy()
    show = show[["Date","Lender","LoanType","Principal","InterestRateAPR","TermMonths","PaymentAmount","Balance","EstMonthsLeft","Notes"]]
    show["Date"] = show["Date"].dt.date.astype(str)
    show["Principal"] = show["Principal"].map(lambda x: f"${x:,.2f}")
    show["PaymentAmount"] = show["PaymentAmount"].map(lambda x: f"${x:,.2f}")
    show["Balance"] = show["Balance"].map(lambda x: f"${x:,.2f}")
    show["InterestRateAPR"] = show["InterestRateAPR"].map(lambda x: f"{x:.2f}%")
    show["EstMonthsLeft"] = show["EstMonthsLeft"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "")

    thead = "<thead><tr>" + "".join(f"<th style='text-align:left;border-bottom:1px solid #ddd;padding:6px'>{c}</th>" for c in show.columns) + "</tr></thead>"
    rows=[]
    for _, r in show.iterrows():
        tds = "".join(f"<td style='padding:6px;border-bottom:1px solid #f0f0f0'>{r[c]}</td>" for c in show.columns)
        rows.append(f"<tr>{tds}</tr>")
    tbl_html = f"""
    <input id="loanSearch" placeholder="Search Lender or Notes..." style="margin:8px 0;padding:6px;width:50%;font-family:system-ui"/>
    <table id='loansTable' style='width:100%;border-collapse:collapse;font-family:system-ui'>
      {thead}<tbody>{''.join(rows)}</tbody>
    </table>
    <script>
      const lb = document.getElementById('loanSearch');
      const ltbl = document.getElementById('loansTable').getElementsByTagName('tbody')[0];
      lb.addEventListener('input', () => {{
        const q = lb.value.toLowerCase();
        for (const row of ltbl.rows) {{
          const lender = row.cells[1].innerText.toLowerCase();
          const notes  = row.cells[9].innerText.toLowerCase();
          row.style.display = (lender.includes(q) || notes.includes(q)) ? '' : 'none';
        }}
      }});
    </script>
    """

    html = [
      "<html><head><meta charset='utf-8'><title>Loans</title></head><body>",
      "<h1 style='font-family:system-ui;margin:12px 16px'>Loans</h1>",
      tiles.to_html(full_html=False, include_plotlyjs='cdn'),
      "<h2 style='font-family:system-ui;margin:12px 16px 0'>Outstanding Balance by Loan Type</h2>",
      fig_bal.to_html(full_html=False, include_plotlyjs=False),
      "<h2 style='font-family:system-ui;margin:12px 16px 0'>Original Principal by Loan Type</h2>",
      fig_prin.to_html(full_html=False, include_plotlyjs=False),
      "<h2 style='font-family:system-ui;margin:12px 16px 0'>All Loans</h2>",
      tbl_html,
      "</body></html>"
    ]
    Path(out_html).write_text("\n".join(html), encoding="utf-8")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    build_loans_dashboard(args.csv, args.out)
