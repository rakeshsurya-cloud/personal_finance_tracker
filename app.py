import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os
import sys

# Add current directory to path so we can import local modules
sys.path.append(str(Path(__file__).parent))

from process_transactions import process_directory, classify_transactions, load_model
from dashboard import _prep, _kpis, cat_spend, income_vs_expense_monthly, net_cashflow_month, top_merchants, recurring_vs_onetime
from loans import _prep_loans, simulate_payoff
from insights import detect_anomalies, predict_spending
from storage import save_file, load_file, list_files

# --- Configuration ---
st.set_page_config(page_title="Family Finance Tracker", layout="wide", page_icon="💰")

# --- Constants ---
DATA_DIR = "bank_data" # Relative folder name for storage module
OUTPUT_DIR = "output"
MODEL_PATH = Path("personal_finance_tracker/models/transaction_classifier.pkl")
LOANS_FILE = "loans.csv"
CATEGORIZED_FILE = "categorized_transactions.csv"

# --- Authentication ---
def check_login():
    """Returns `True` if the user is logged in."""
    
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["role"] = None

    if st.session_state["authenticated"]:
        return True

    st.header("🔐 Login")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state["authenticated"] = True
            st.session_state["role"] = "admin"
            st.success("Logged in as Admin")
            st.experimental_rerun()
        elif username == "viewer" and password == "viewer123":
            st.session_state["authenticated"] = True
            st.session_state["role"] = "viewer"
            st.success("Logged in as Viewer")
            st.experimental_rerun()
        else:
            st.error("Incorrect username or password")
            
    return False

if not check_login():
    st.stop()

# Role Helper
def is_admin():
    return st.session_state.get("role") == "admin"

# --- Main App ---
st.title(f"💰 Family Finance Tracker ({st.session_state['role'].title()} Mode)")

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Sidebar
with st.sidebar:
    st.header("Data Management")
    
    if is_admin():
        # File Uploader
        uploaded_files = st.file_uploader("Upload Bank Statements (CSV/XLSX)", accept_multiple_files=True)
        if uploaded_files:
            for uploaded_file in uploaded_files:
                # Save file using storage module
                save_file(uploaded_file.name, uploaded_file.getbuffer(), DATA_DIR)
            st.success(f"Uploaded {len(uploaded_files)} files.")
            
            # Trigger processing
            if st.button("Process New Files"):
                with st.spinner("Processing and Categorizing..."):
                    try:
                        # Note: process_directory still expects local files. 
                        # For S3, we'd need to refactor process_transactions.py to read from S3 or download first.
                        # For this iteration, we assume local is available or we download temp.
                        # A full S3 refactor of process_transactions is out of scope for this quick step, 
                        # but we can at least save the output to S3.
                        
                        # Temporary fix: Ensure local files exist for processing script
                        # In a real S3-only env, we would rewrite process_directory to take bytes.
                        df = process_directory(f"personal_finance_tracker/{DATA_DIR}", str(MODEL_PATH))
                        
                        # Save output to storage
                        save_file(CATEGORIZED_FILE, df, OUTPUT_DIR)
                        st.success("Processing Complete!")
                    except Exception as e:
                        st.error(f"Error processing files: {e}")

        st.markdown("---")
        st.header("Settings")
        if st.button("Clear All Data"):
            # Dangerous button to clear data
            # Note: This implementation currently only clears local files.
            # To support S3, we would need to add delete capabilities to storage.py
            
            local_data_dir = Path(f"personal_finance_tracker/{DATA_DIR}")
            if local_data_dir.exists():
                for f in local_data_dir.glob("*"):
                    f.unlink()
            
            local_output_file = Path(f"personal_finance_tracker/{OUTPUT_DIR}/{CATEGORIZED_FILE}")
            if local_output_file.exists():
                local_output_file.unlink()
                
            st.warning("All data cleared.")
            st.experimental_rerun()
    else:
        st.info("🔒 Admin access required to upload files or clear data.")

# Load Data
df = load_file(CATEGORIZED_FILE, OUTPUT_DIR)
if df is not None:
    df = _prep(df)
else:
    df = pd.DataFrame()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "💳 Transactions", "💸 Loans & Payoff", "🧠 Smart Insights", "⚙️ Connect"])

with tab1:
    if df.empty:
        st.info("No transaction data found. Please upload bank statements in the sidebar.")
    else:
        # KPIs
        kpi_fig = _kpis(df)
        st.plotly_chart(kpi_fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(cat_spend(df), use_container_width=True)
            st.plotly_chart(top_merchants(df), use_container_width=True)
        with col2:
            st.plotly_chart(income_vs_expense_monthly(df), use_container_width=True)
            st.plotly_chart(net_cashflow_month(df), use_container_width=True)
            
        st.plotly_chart(recurring_vs_onetime(df), use_container_width=True)

with tab2:
    if df.empty:
        st.info("No transactions to display.")
    else:
        st.subheader("Transaction Log")
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("Search Description")
        with col2:
            categories = ["All"] + sorted(df["Category"].unique().tolist())
            selected_cat = st.selectbox("Filter by Category", categories)
            
        filtered_df = df.copy()
        if search_term:
            filtered_df = filtered_df[filtered_df["Description"].str.contains(search_term, case=False)]
        if selected_cat != "All":
            filtered_df = filtered_df[filtered_df["Category"] == selected_cat]
            
        # Editable Dataframe (experimental)
        if is_admin():
            edited_df = st.data_editor(
                filtered_df[["Date", "Description", "Amount", "Category"]],
                num_rows="dynamic",
                use_container_width=True
            )
            
            # Note: Saving edits back to CSV is complex in Streamlit without a database, 
            # but we can overwrite the CSV if the user clicks a save button.
            if st.button("Save Changes"):
                # Update the main dataframe with edits
                # This is a simplified approach; in production, you'd merge on ID
                # For now, we just save the filtered view or warn user
                st.warning("Saving edits directly to CSV is not fully implemented in this demo version to prevent data loss. In a real app, this would update the database.")
        else:
            st.dataframe(filtered_df[["Date", "Description", "Amount", "Category"]], use_container_width=True)

with tab3:
    st.header("Loan Tracker & Payoff Simulator")
    
    # Loan Data Input (if no file exists)
    loans_df = load_file(LOANS_FILE, "loans") # Special folder or root? Let's use 'loans' folder or just root. 
    # Actually storage.py defaults to bank_data. Let's use a specific folder or just root.
    # Let's assume loans are in 'bank_data' for simplicity or root. 
    # storage.py saves to personal_finance_tracker/{folder}. 
    # Let's use folder="" for root of tracker? No, let's use "data".
    
    # Correction: storage.py uses "bank_data" default. Let's put loans in "data".
    
    loans_df = load_file(LOANS_FILE, "data")

    if loans_df is None:
        st.info("No loan data found. Create a `loans.csv` or enter data below.")
        
        default_loans = pd.DataFrame({
            "Lender": ["Bank A", "Credit Card B"],
            "LoanType": ["Mortgage", "Credit Card"],
            "Principal": [250000, 5000],
            "InterestRateAPR": [4.5, 18.99],
            "TermMonths": [360, 0],
            "PaymentAmount": [1266, 150],
            "Balance": [240000, 4800],
            "Date": [pd.Timestamp.now().date(), pd.Timestamp.now().date()]
        })
        
        edited_loans = st.data_editor(default_loans, num_rows="dynamic", disabled=not is_admin())
        if is_admin() and st.button("Save Loan Data"):
            save_file(LOANS_FILE, edited_loans, "data")
            st.experimental_rerun()
    else:
        loans_df = _prep_loans(loans_df)
        
        # Overview
        col1, col2, col3 = st.columns(3)
        total_debt = loans_df["Balance"].sum()
        avg_rate = (loans_df["Balance"] * loans_df["InterestRateAPR"]).sum() / total_debt if total_debt > 0 else 0
        
        col1.metric("Total Debt", f"${total_debt:,.0f}")
        col2.metric("Weighted Avg APR", f"{avg_rate:.2f}%")
        col3.metric("Monthly Minimums", f"${loans_df['PaymentAmount'].sum():,.0f}")
        
        st.dataframe(loans_df[["Lender", "LoanType", "Balance", "InterestRateAPR", "PaymentAmount", "EstMonthsLeft"]])
        
        st.markdown("---")
        st.subheader("🚀 Payoff Simulator")
        
        loan_to_simulate = st.selectbox("Select Loan to Simulate", loans_df["Lender"].unique())
        
        if loan_to_simulate:
            loan_data = loans_df[loans_df["Lender"] == loan_to_simulate].iloc[0]
            
            st.write(f"**Simulating: {loan_data['Lender']}** (Balance: ${loan_data['Balance']:,.2f}, Rate: {loan_data['InterestRateAPR']}%)")
            
            col1, col2 = st.columns(2)
            with col1:
                extra_payment = st.slider("Extra Monthly Payment ($)", 0, 2000, 0, step=50)
            
            schedule = simulate_payoff(
                loan_data["Balance"], 
                loan_data["InterestRateAPR"], 
                loan_data["PaymentAmount"], 
                extra_payment
            )
            
            if not schedule.empty:
                months_saved = loan_data["EstMonthsLeft"] - len(schedule)
                total_interest = schedule["Interest"].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("New Payoff Time", f"{len(schedule)/12:.1f} years", delta=f"-{months_saved/12:.1f} years")
                c2.metric("Total Interest Paid", f"${total_interest:,.0f}")
                c3.metric("Total Cost", f"${schedule['TotalPayment'].sum() + loan_data['Balance']:,.0f}")
                
                # Chart
                fig = px.area(schedule, x="Month", y="Balance", title="Projected Balance Over Time")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("Payment too low to cover interest! You will never pay this off.")

with tab4:
    st.header("🧠 Smart Insights")
    if df.empty:
        st.info("Upload data to see insights.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔮 Spending Forecast")
            st.markdown("Based on your historical data, here is a prediction for next month.")
            fig_forecast = predict_spending(df)
            st.plotly_chart(fig_forecast, use_container_width=True)
            
        with col2:
            st.subheader("🚨 Anomaly Detection")
            st.markdown("These transactions look unusual compared to your normal spending.")
            
            df_anom = detect_anomalies(df)
            anomalies = df_anom[df_anom["IsAnomaly"] == True]
            
            if not anomalies.empty:
                st.dataframe(anomalies[["Date", "Description", "Amount", "Category"]].style.format({"Amount": "${:.2f}"}))
            else:
                st.success("No anomalies detected! Your spending looks normal.")

with tab5:
    st.header("⚙️ Bank Connect")
    
    if is_admin():
        st.markdown("""
        Connect your bank accounts directly to import transactions automatically.
        
        > **Note**: This feature requires a **Plaid API Key**. If you don't have one, please stick to manual CSV uploads.
        """)
        
        with st.expander("Configure Plaid"):
            client_id = st.text_input("Plaid Client ID")
            secret = st.text_input("Plaid Secret", type="password")
            env = st.selectbox("Environment", ["Sandbox", "Development", "Production"])
            
            if st.button("Save Configuration"):
                st.success("Configuration saved (simulated). In a real app, this would encrypt and store your keys.")
                
        st.subheader("Connected Accounts")
        st.info("No accounts connected yet.")
        if st.button("➕ Add New Account"):
            st.warning("Plaid Link would open here.")
    else:
        st.info("🔒 Admin access required to configure bank connections.")


