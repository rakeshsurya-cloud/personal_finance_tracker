import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import os
import sys
import bcrypt
import time

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from database import SessionLocal, User, Transaction, Loan, FixedExpense
from process_transactions import process_files, save_to_db
from plaid_integration import create_link_token, exchange_public_token, fetch_transactions
from dashboard import _prep, _kpis, cat_spend, income_vs_expense_monthly, net_worth_trend
from loans import _prep_loans, simulate_payoff
from insights import detect_anomalies, predict_spending

# --- Configuration ---
st.set_page_config(page_title="Family Finance Tracker", layout="wide", page_icon="💰")
MODEL_PATH = Path("personal_finance_tracker/models/transaction_classifier.pkl")

# --- Database Session ---
if "db" not in st.session_state:
    st.session_state.db = SessionLocal()

def get_db():
    return st.session_state.db

# --- Authentication ---
def check_login():
    """Neon login page with floating orbs"""
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["role"] = None
        st.session_state["user_id"] = None
        st.session_state["show_password"] = False
    
    # If already authenticated, return True immediately
    if st.session_state.get("authenticated", False):
        return True
    
    # Show login page
    st.markdown("""
    <style>
        /* Hide Streamlit elements */
        #MainMenu, footer, header {visibility: hidden;}
        .stApp > header {visibility: hidden;}

        /* Full viewport setup */
        .stApp {
            background: #0f0f12 !important;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .block-container {
            padding: 2rem 1rem !important;
            max-width: 500px !important;
        }

        /* Floating glow orbs */
        .stApp::before,
        .stApp::after {
            content: '';
            position: fixed;
            border-radius: 50%;
            filter: blur(100px);
            opacity: 0.3;
            pointer-events: none;
            z-index: 0;
        }

        .stApp::before {
            width: 400px;
            height: 400px;
            background: linear-gradient(135deg, #08cac1, #0f4c81);
            top: -100px;
            left: -100px;
            animation: float1 8s ease-in-out infinite;
        }

        .stApp::after {
            width: 350px;
            height: 350px;
            background: linear-gradient(135deg, #0891b2, #6366f1);
            bottom: -100px;
            right: -100px;
            animation: float2 8s ease-in-out infinite 4s;
        }

        @keyframes float1 {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(30px, 30px); }
        }

        @keyframes float2 {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(-30px, -30px); }
        }

        /* Card slide-up animation */
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        /* Login card container */
        .login-card {
            position: relative;
            z-index: 1;
            background: rgba(21, 21, 28, 0.8);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 48px 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            animation: slideUp 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* Input fields */
        .stTextInput > div > div > input {
            background: rgba(30, 30, 40, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            color: #fff !important;
            font-size: 15px !important;
            padding: 16px !important;
            transition: all 0.3s ease !important;
        }

        .stTextInput > div > div > input:focus {
            border-color: #08cac1 !important;
            box-shadow: 0 0 0 3px rgba(8, 202, 193, 0.1), 0 0 20px rgba(8, 202, 193, 0.3) !important;
            background: rgba(30, 30, 40, 0.8) !important;
        }

        .stTextInput > div > div > input::placeholder {
            color: #6b7280 !important;
        }

        .stTextInput label {
            color: #9ca3af !important;
            font-size: 14px !important;
            display: none !important;
        }
        
        /* Hide label visibility */
        .stTextInput > label {
            display: none !important;
        }

        /* Primary button (Sign In) */
        .stButton > button[kind="primary"],
        .stButton > button:not([kind="secondary"]) {
            width: 100% !important;
            background: linear-gradient(135deg, #08cac1, #0891b2) !important;
            color: #1a1a1a !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 16px !important;
            font-size: 15px !important;
            font-weight: 600 !important;
            letter-spacing: 1px !important;
            text-transform: uppercase !important;
            transition: all 0.3s ease !important;
        }

        .stButton > button[kind="primary"]:hover,
        .stButton > button:not([kind="secondary"]):hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 30px rgba(8, 202, 193, 0.4) !important;
        }

        /* Secondary button (Password toggle) */
        .stButton > button[kind="secondary"] {
            background: transparent !important;
            color: #9ca3af !important;
            border: none !important;
            padding: 4px 8px !important;
            min-width: auto !important;
            width: auto !important;
            font-size: 18px !important;
            box-shadow: none !important;
        }

        .stButton > button[kind="secondary"]:hover {
            color: #08cac1 !important;
            transform: none !important;
            box-shadow: none !important;
            background: transparent !important;
        }

        /* Checkbox */
        .stCheckbox {
            color: #9ca3af !important;
            font-size: 14px !important;
        }

        .stCheckbox label {
            color: #9ca3af !important;
        }

        /* Links */
        a {
            color: #08cac1 !important;
            text-decoration: none !important;
            transition: color 0.3s ease !important;
        }

        a:hover {
            color: #0ab5ad !important;
        }

        /* Error/Success messages */
        .stAlert {
            background: rgba(30, 30, 40, 0.8) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }

        /* Mobile responsive */
        @media (max-width: 600px) {
            .login-card {
                padding: 32px 24px !important;
            }

            .block-container {
                padding: 1rem 0.5rem !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # Start login card
    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    # Header with SEELAM logo
    st.markdown("""
    <div style="text-align: center; margin-bottom: 40px;">
        <h1 style="
            color: #08cac1;
            font-size: 48px;
            font-weight: 700;
            margin: 0 0 16px 0;
            letter-spacing: 3px;
            filter: drop-shadow(0 0 20px rgba(8, 202, 193, 0.6));
            font-family: 'Segoe UI', sans-serif;
        ">SEELAM</h1>
        <h2 style="
            color: #fff;
            font-size: 28px;
            font-weight: 600;
            margin: 0 0 8px 0;
            letter-spacing: 0.5px;
        ">Sign In</h2>
        <p style="
            color: #9ca3af;
            font-size: 14px;
            margin: 0;
        ">Access your account</p>
    </div>
    """, unsafe_allow_html=True)

    # Form inputs
    username = st.text_input("Email", placeholder="Enter your email", key="login_user")
    password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")

    # Forgot password link
    st.markdown("""
    <div style="text-align: right; margin-top: -8px; margin-bottom: 16px;">
        <a href="#" style="font-size: 14px; color: #9ca3af;">Forgot password?</a>
    </div>
    """, unsafe_allow_html=True)

    # Sign in button
    if st.button("Sign In", key="login_btn", type="primary", use_container_width=True):
        db = get_db()
        user = db.query(User).filter(User.username == username).first()

        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            st.session_state["authenticated"] = True
            st.session_state["role"] = user.role
            st.session_state["user_id"] = user.id
            st.success("✅ Login successful!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

    # Demo credentials
    st.markdown("""
    <div style="text-align: center; margin-top: 32px; padding-top: 24px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
        <p style="color: #6b7280; font-size: 13px; margin: 0; line-height: 1.6;">
            <strong style="color: #9ca3af;">Demo Credentials:</strong><br>
            Admin: <span style="color: #08cac1; font-weight: 600;">admin</span> / <span style="color: #08cac1;">admin123</span><br>
            Family: <span style="color: #08cac1; font-weight: 600;">brother</span> / <span style="color: #08cac1;">brother123</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # End login card
    st.markdown('</div>', unsafe_allow_html=True)

    # Return authentication status
    return st.session_state.get("authenticated", False)

if not check_login():
    st.stop()

# Reset CSS for main app - restore normal layout
st.markdown("""
<style>
    /* Reset background */
    .stApp {
        background: #ffffff !important;
        display: block !important;
        align-items: unset !important;
        justify-content: unset !important;
        min-height: unset !important;
        position: static !important;
        overflow: auto !important;
    }
    
    /* Reset block container for normal layout */
    .block-container {
        padding: 3rem 1rem 10rem !important;
        max-width: 1200px !important;
    }
    
    /* Remove pseudo-elements (orbs) */
    .stApp::before,
    .stApp::after {
        display: none !important;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .block-container {
            padding: 2rem 1rem !important;
            max-width: 100% !important;
        }
        
        /* Stack metrics vertically on mobile */
        [data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
        }
        
        /* Make charts responsive */
        .js-plotly-plot {
            width: 100% !important;
        }
        
        /* Adjust sidebar */
        [data-testid="stSidebar"] {
            width: 100% !important;
        }
    }
    
    /* Tablet view */
    @media (min-width: 769px) and (max-width: 1024px) {
        .block-container {
            padding: 2.5rem 1.5rem !important;
            max-width: 900px !important;
        }
    }
    
    /* Desktop view */
    @media (min-width: 1025px) {
        .block-container {
            padding: 3rem 1rem 10rem !important;
            max-width: 1200px !important;
        }
    }
    
    /* General improvements */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
    }
</style>
""", unsafe_allow_html=True)

# Role Helper
def is_admin():
    return st.session_state.get("role") == "admin"

# --- Data Loading ---
def load_data():
    db = get_db()
    query = db.query(Transaction)
    
    # RBAC Filtering
    if not is_admin():
        # Family only sees shared transactions
        query = query.filter(Transaction.is_shared == True)
        
    transactions = query.all()
    
    if not transactions:
        return pd.DataFrame()
        
    data = [{
        "Date": t.date,
        "Description": t.description,
        "Amount": t.amount,
        "Category": t.category,
        "IsShared": t.is_shared,
        "ID": t.id
    } for t in transactions]
    
    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

# --- Main App ---
st.title(f"💰 Family Finance Tracker ({st.session_state['role'].title()} Mode)")



# Sidebar
with st.sidebar:
    st.header("Data Management")
    
    if is_admin():
        # File Upload
        uploaded_files = st.file_uploader(
            "Upload Bank CSVs",
            type=["csv"],
            accept_multiple_files=True,
            help="Upload transaction CSV files from your bank"
        )
        
        if uploaded_files:
            saved_paths = []
            for uploaded_file in uploaded_files:
                path = Path("temp") / uploaded_file.name
                path.parent.mkdir(exist_ok=True)
                with open(path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                saved_paths.append(path)
            
            # Process
            with st.spinner("Processing..."):
                try:
                    df_new = process_files(saved_paths, str(MODEL_PATH))
                    if not df_new.empty:
                        count = save_to_db(df_new, get_db())
                        st.success(f"Imported {count} new transactions!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("No valid transactions found.")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    # Cleanup
                    for p in saved_paths:
                        p.unlink()
        
        st.divider()
        
        # Plaid Connection
        st.subheader("🏦 Connect Bank (Plaid)")
        if st.button("Connect Bank Account", use_container_width=True):
            try:
                link_token = create_link_token()
                if link_token:
                    st.info("Open plaid_test.html in your browser to complete connection")
                    st.code(f"Link Token: {link_token}", language="text")
                else:
                    st.error("Failed to create link token")
            except Exception as e:
                st.error(f"Error: {e}")
        
        public_token = st.text_input("Paste Public Token from Plaid Link", key="plaid_public_token")
        if st.button("Exchange Token", use_container_width=True) and public_token:
            try:
                access_token = exchange_public_token(public_token)
                if access_token:
                    st.success("Connected! Fetching transactions...")
                    txns = fetch_transactions(access_token)
                    if txns:
                        st.success(f"Fetched {len(txns)} transactions")
                        # Save to database logic here
                    else:
                        st.warning("No transactions found")
                else:
                    st.error("Failed to exchange token")
            except Exception as e:
                st.error(f"Error: {e}")
    
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# Load Data
df = load_data()
if not df.empty:
    df_prep = _prep(df)
else:
    df_prep = pd.DataFrame()

# Tabs (removed Connect tab - moved to sidebar)
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "💳 Transactions", "💸 Loans", "📅 Fixed Expenses", "🧠 Insights"])

with tab4:
    st.header("📅 Fixed Expenses & Budgeting")
    
    db = get_db()
    
    # Add New Expense Form
    if is_admin():
        with st.expander("➕ Add New Fixed Expense"):
            with st.form("add_fixed_expense"):
                col1, col2 = st.columns(2)
                name = col1.text_input("Expense Name (e.g., Rent)")
                amount = col2.number_input("Amount ($)", min_value=0.0, step=10.0)
                
                col3, col4 = st.columns(2)
                due_day = col3.number_input("Due Day (1-31)", min_value=1, max_value=31)
                priority = col4.selectbox("Priority", ["Critical", "High", "Medium", "Low"])
                
                is_shared = st.checkbox("Share with Family?", value=True)
                
                if st.form_submit_button("Add Expense"):
                    new_exp = FixedExpense(name=name, amount=amount, due_date=due_day, priority=priority, is_shared=is_shared)
                    db.add(new_exp)
                    db.commit()
                    st.success("Added!")
                    st.rerun()

    # List Expenses
    expenses = db.query(FixedExpense).all()
    visible_expenses = [e for e in expenses if is_admin() or e.is_shared]
    
    if visible_expenses:
        data = [{
            "Name": e.name, "Amount": e.amount, "Due Day": e.due_date, 
            "Priority": e.priority, "Shared": e.is_shared, "ID": e.id
        } for e in visible_expenses]
        
        df_exp = pd.DataFrame(data)
        
        # Priority Color Logic
        def color_priority(val):
            color = 'red' if val == 'Critical' else 'orange' if val == 'High' else 'green'
            return f'color: {color}'

        st.dataframe(df_exp.style.applymap(color_priority, subset=['Priority']), use_container_width=True)
        
        # Total Fixed Cost
        total_fixed = df_exp["Amount"].sum()
        st.metric("Total Monthly Fixed Expenses", f"${total_fixed:,.2f}")
        
        # Delete (Admin only)
        if is_admin():
            to_delete = st.selectbox("Select to Delete", df_exp["Name"])
            if st.button("Delete Selected"):
                db.query(FixedExpense).filter(FixedExpense.name == to_delete).delete()
                db.commit()
                st.rerun()
    else:
        st.info("No fixed expenses added yet.")


with tab1:
    if df_prep.empty:
        st.info("No data available.")
    else:
        # Calculate Total Fixed Expenses
        fixed_expenses_total = db.query(FixedExpense).with_entities(FixedExpense.amount).all()
        fixed_total_val = sum([x[0] for x in fixed_expenses_total])

        _kpis(df_prep, fixed_expenses_total=fixed_total_val)
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(cat_spend(df_prep), use_container_width=True)
        with col2:
            st.plotly_chart(income_vs_expense_monthly(df_prep), use_container_width=True)
            
        st.subheader("📈 Financial Health")
        st.plotly_chart(net_worth_trend(df_prep), use_container_width=True)

with tab2:
    st.subheader("Transaction Log")
    if df.empty:
        st.info("No transactions.")
    else:
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("Search")
        with col2:
            cats = ["All"] + sorted(df["Category"].unique().tolist())
            sel_cat = st.selectbox("Category", cats)
            
        filt_df = df.copy()
        if search_term:
            filt_df = filt_df[filt_df["Description"].str.contains(search_term, case=False)]
        if sel_cat != "All":
            filt_df = filt_df[filt_df["Category"] == sel_cat]
            
        # Admin Editing
        if is_admin():
            st.info("💡 Edit 'IsShared' to share with family.")
            edited_df = st.data_editor(
                filt_df[["Date", "Description", "Amount", "Category", "IsShared", "ID"]],
                key="txn_editor",
                disabled=["ID"],
                hide_index=True,
                use_container_width=True
            )
            
            if st.button("Save Changes"):
                db = get_db()
                changes = st.session_state["txn_editor"]["edited_rows"]
                for idx, change in changes.items():
                    real_id = filt_df.iloc[idx]["ID"]
                    txn = db.query(Transaction).filter(Transaction.id == real_id).first()
                    if txn:
                        if "Category" in change: txn.category = change["Category"]
                        if "IsShared" in change: txn.is_shared = change["IsShared"]
                        if "Amount" in change: txn.amount = change["Amount"]
                        if "Description" in change: txn.description = change["Description"]
                
                db.commit()
                st.success("Saved!")
                st.rerun()
        else:
            st.dataframe(filt_df[["Date", "Description", "Amount", "Category"]], use_container_width=True)

with tab3:
    st.header("💸 Debt Management")
    
    db = get_db()
    
    # Add New Loan Form
    if is_admin():
        with st.expander("➕ Add New Loan"):
            with st.form("add_loan"):
                col1, col2 = st.columns(2)
                lender = col1.text_input("Lender Name")
                principal = col2.number_input("Principal Balance ($)", min_value=0.0)
                
                col3, col4 = st.columns(2)
                rate = col3.number_input("Interest Rate (%)", min_value=0.0, step=0.1)
                payment = col4.number_input("Min Monthly Payment ($)", min_value=0.0)
                
                is_shared = st.checkbox("Share with Family?", value=False)
                
                if st.form_submit_button("Add Loan"):
                    new_loan = Loan(lender=lender, principal=principal, balance=principal, interest_rate=rate, min_payment=payment, term_months=360, is_shared=is_shared)
                    db.add(new_loan)
                    db.commit()
                    st.success("Loan Added!")
                    st.rerun()

    # List Loans
    loans = db.query(Loan).all()
    visible_loans = [l for l in loans if is_admin() or l.is_shared]
    
    if visible_loans:
        # Summary Cards
        total_debt = sum([l.balance for l in visible_loans])
        total_pmt = sum([l.min_payment for l in visible_loans])
        
        c1, c2 = st.columns(2)
        c1.metric("Total Outstanding Debt", f"${total_debt:,.0f}")
        c2.metric("Total Monthly Payments", f"${total_pmt:,.0f}")
        
        # Detailed Table
        l_data = [{
            "Lender": l.lender, "Balance": l.balance, "Rate": f"{l.interest_rate}%", 
            "Min Payment": l.min_payment, "Shared": l.is_shared
        } for l in visible_loans]
        st.dataframe(pd.DataFrame(l_data), use_container_width=True)
        
        # Amortization Simulator (Simple)
        st.subheader("📉 Payoff Simulator")
        selected_loan_name = st.selectbox("Select Loan to Simulate", [l.lender for l in visible_loans])
        selected_loan = next(l for l in visible_loans if l.lender == selected_loan_name)
        
        extra_pmt = st.slider("Extra Monthly Payment ($)", 0, 2000, 100)
        
        # Simulate
        # (Using simplified logic here instead of calling loans.py for speed)
        balance = selected_loan.balance
        rate_monthly = (selected_loan.interest_rate / 100) / 12
        pmt = selected_loan.min_payment + extra_pmt
        
        months = 0
        balances = [balance]
        while balance > 0 and months < 360:
            interest = balance * rate_monthly
            principal_paid = pmt - interest
            balance -= principal_paid
            balances.append(max(0, balance))
            months += 1
            
        st.line_chart(balances)
        st.caption(f"With ${extra_pmt} extra, you'll be debt-free in **{months // 12} years and {months % 12} months**!")

    else:
        st.info("No loans found.")

with tab5:
    st.header("🧠 Smart Insights")
    
    if not df_prep.empty:
        from insights import generate_actionable_tips
        tips = generate_actionable_tips(df_prep)
        
        if tips:
            for tip in tips:
                st.markdown(f"""
                <div style="padding:15px; background-color:#f0f2f6; border-radius:10px; margin-bottom:10px">
                    {tip}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Your finances look stable! No alerts this month.")
            
        st.subheader("🔮 Spending Forecast")
        st.plotly_chart(predict_spending(df_prep), use_container_width=True)
    else:
        st.info("Need transaction data to generate insights.")

with tab5:
    st.header("Connect Bank (Plaid)")
    if is_admin():
        st.write("Link your bank account to fetch transactions automatically.")
        
        # In a real app, we'd use a frontend component to handle the Link flow.
        # Here we simulate the exchange or allow manual public token entry (dev mode).
        
        if st.button("🔗 Start Plaid Link (Sandbox)"):
            try:
                link_token = create_link_token(str(st.session_state["user_id"]))
                st.info(f"Link Token Created: `{link_token}`")
                st.markdown("""
                **Instructions:**
                1. Use a Plaid Link frontend (e.g., React app or HTML test file) with this token.
                2. Complete the flow to get a **Public Token**.
                3. Enter the Public Token below.
                """)
            except Exception as e:
                st.error(f"Plaid Error: {e}")
                
        public_token = st.text_input("Enter Public Token (from Link flow)")
        if st.button("Exchange & Sync"):
            if public_token:
                try:
                    access_token, item_id = exchange_public_token(public_token)
                    st.success(f"Connected! Item ID: {item_id}")
                    
                    # Fetch initial transactions
                    resp = fetch_transactions(access_token)
                    transactions = resp['added']
                    
                    if transactions:
                        db = get_db()
                        count = 0
                        for t in transactions:
                            # Check for duplicates
                            exists = db.query(Transaction).filter(Transaction.plaid_transaction_id == t['transaction_id']).first()
                            if not exists:
                                # Simple auto-categorization fallback if model not used here yet
                                # In future, we can run the classifier on t['name']
                                
                                new_txn = Transaction(
                                    date=pd.to_datetime(t['date']).date(),
                                    description=t['name'],
                                    amount=t['amount'],
                                    category=t['category'][0] if t['category'] else "Uncategorized",
                                    source="plaid",
                                    plaid_transaction_id=t['transaction_id'],
                                    is_shared=False
                                )
                                db.add(new_txn)
                                count += 1
                        db.commit()
                        st.success(f"Imported {count} new transactions from Plaid!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.info("No new transactions found.")
                        
                except Exception as e:
                    st.error(f"Exchange Error: {e}")
    else:
        st.error("Admin only.")
