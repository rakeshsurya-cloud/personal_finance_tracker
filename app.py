import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import os
import sys
import bcrypt
import time
from datetime import datetime

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from database import SessionLocal, User, Transaction, Loan, FixedExpense, PlaidItem, CategoryBudget, NetWorthSnapshot, init_db
from process_transactions import process_files, save_to_db
from plaid_integration import create_link_token, exchange_public_token, fetch_transactions
from dashboard import _prep, _kpis, cat_spend, income_vs_expense_monthly, net_worth_trend
from loans import _prep_loans, simulate_payoff
from insights import (
    assistant_response,
    compute_highlights,
    detect_anomalies,
    generate_actionable_tips,
    predict_spending,
    summarize_budget_watch,
)

# --- Configuration ---
st.set_page_config(page_title="Family Finance Tracker", layout="wide", page_icon="💰")
MODEL_PATH = Path("personal_finance_tracker/models/transaction_classifier.pkl")

# --- Database Session ---
init_db()

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
        st.session_state["failed_attempts"] = []
        st.session_state["lock_until"] = None
        st.session_state["preview_as_family"] = False
    
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
    pass_col, toggle_col = st.columns([4, 1])
    with pass_col:
        password = st.text_input(
            "Password",
            # Streamlit accepts only "default" or "password" types.
            type="default" if st.session_state.get("show_password") else "password",
            placeholder="Enter your password",
            key="login_pass",
        )
    with toggle_col:
        toggle_label = "🙈 Hide" if st.session_state.get("show_password") else "👁️ Show"
        if st.button(toggle_label, key="toggle_password", type="secondary"):
            st.session_state["show_password"] = not st.session_state["show_password"]
            st.rerun()

    # Forgot password link
    if st.button("Forgot password?", key="forgot_pw", type="secondary"):
        st.info("Password recovery is handled by the support team. Please email support@example.com with your registered email.")

    # Sign in button
    now = time.time()
    lock_until = st.session_state.get("lock_until")
    if lock_until and now < lock_until:
        wait_for = int(lock_until - now)
        st.error(f"Too many failed attempts. Please wait {wait_for} seconds before trying again.")
        st.caption("Tip: enable MFA/2FA in your identity provider for added protection.")
    elif st.button("Sign In", key="login_btn", type="primary", use_container_width=True):
        # Prune stale attempts (keep last 5 minutes)
        st.session_state["failed_attempts"] = [t for t in st.session_state.get("failed_attempts", []) if now - t < 300]

        db = get_db()
        user = db.query(User).filter(User.username == username).first()

        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            st.session_state["authenticated"] = True
            st.session_state["role"] = user.role
            st.session_state["user_id"] = user.id
            st.session_state["failed_attempts"] = []
            st.session_state["lock_until"] = None
            st.success("✅ Login successful!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.session_state["failed_attempts"].append(now)
            st.error("❌ Invalid credentials")
            print(f"Failed login attempt for user {username} at {time.strftime('%Y-%m-%d %H:%M:%S')}")

            if len(st.session_state["failed_attempts"]) >= 5:
                st.session_state["lock_until"] = now + 60
                st.warning("Too many failed attempts. Login temporarily locked for 60 seconds.")

    st.caption("For security, we recommend enabling MFA/2FA on your identity provider.")

    # Demo credentials (hidden unless explicitly allowed)
    show_demo_creds = os.getenv("SHOW_DEMO_CREDENTIALS", "false").lower() == "true"
    if show_demo_creds:
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
    return st.session_state.get("role") == "admin" and not st.session_state.get("preview_as_family")

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
        "Category": t.category or "Uncategorized",
        "IsShared": t.is_shared,
        "ID": t.id
    } for t in transactions]
    
    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Category"] = df["Category"].fillna("Uncategorized").replace("", "Uncategorized")
    return df


def upsert_plaid_item(item_id: str, access_token: str, institution_name: str = "Unknown Institution") -> PlaidItem:
    db = get_db()
    item = db.query(PlaidItem).filter(PlaidItem.item_id == item_id).first()
    if not item:
        item = PlaidItem(item_id=item_id, access_token=access_token, institution_name=institution_name)
        db.add(item)
    else:
        item.access_token = access_token
        if institution_name:
            item.institution_name = institution_name
    db.commit()
    return item


def sync_plaid_transactions(item: PlaidItem, share_with_family: bool = True):
    db = get_db()
    total_new = 0
    cursor = item.cursor
    latest_cursor = cursor
    has_more = True

    while has_more:
        resp = fetch_transactions(item.access_token, cursor=cursor)
        resp_data = resp.to_dict() if hasattr(resp, "to_dict") else resp

        added = resp_data.get("added", [])
        has_more = resp_data.get("has_more", False)
        latest_cursor = resp_data.get("next_cursor", latest_cursor)
        cursor = latest_cursor

        for t in added:
            plaid_id = t.get("transaction_id")
            if plaid_id and db.query(Transaction).filter(Transaction.plaid_transaction_id == plaid_id).first():
                continue

            category_list = t.get("category") or []
            pf_category = None
            if t.get("personal_finance_category"):
                pf_category = t["personal_finance_category"].get("primary")
            category_value = pf_category or (category_list[0] if category_list else "Uncategorized")

            # Plaid convention: Positive = Expense, Negative = Income
            # Our App convention: Positive = Income, Negative = Expense
            raw_amount = t.get("amount", 0)
            signed_amount = -raw_amount

            new_txn = Transaction(
                date=pd.to_datetime(t.get("date")).date(),
                description=t.get("name", "Plaid Transaction"),
                amount=signed_amount,
                category=category_value or "Uncategorized",
                source="plaid",
                plaid_transaction_id=plaid_id,
                is_shared=share_with_family,
            )
            db.add(new_txn)
            total_new += 1

        db.commit()

    item.cursor = latest_cursor
    item.last_synced_at = datetime.utcnow()
    db.commit()
    return total_new


def compute_budget_status(df_prep: pd.DataFrame, budgets: list[CategoryBudget]):
    if df_prep.empty or not budgets:
        return []

    current_month = str(pd.Timestamp.today().strftime("%Y-%m"))
    month_df = df_prep[df_prep["Month"] == current_month]
    expenses = month_df[month_df["Amount"] < 0].copy()
    spent_by_cat = expenses.groupby("Category")["Amount"].sum().abs()

    status = []
    for budget in budgets:
        limit = float(budget.monthly_limit or 0)
        spent = float(spent_by_cat.get(budget.category, 0))
        remaining = limit - spent
        pct = spent / limit if limit > 0 else 0
        status.append({
            "category": budget.category,
            "limit": limit,
            "spent": spent,
            "remaining": remaining,
            "pct": pct,
            "is_over": remaining < 0,
        })
    return status

# --- Main App ---
current_role = st.session_state.get("role") or "family"
if st.session_state.get("preview_as_family") and current_role == "admin":
    display_role = "Family Preview"
else:
    display_role = current_role.title()

st.title(f"💰 Family Finance Tracker ({display_role} Mode)")

if not is_admin():
    st.info("You are viewing shared family data only. Personal transactions remain hidden.")



# Sidebar
with st.sidebar:
    st.header("Access & Roles")
    st.markdown("Admins can view and edit all data. Family users only see records marked as **Shared**, controlled by the `IsShared` column.")
    if st.session_state.get("role") == "admin":
        st.checkbox("Preview as family", key="preview_as_family", help="Temporarily view only shared data to validate visibility.")
    else:
        st.caption("You're in family mode—private items stay hidden unless shared.")

    st.divider()
    st.header("Data Management")

    if is_admin():
        db_sidebar = get_db()
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
        st.subheader("🏦 Bank Sync (Plaid)")
        st.caption("Connect once, then pull fresh transactions with a single click. Imports can be shared with family automatically.")

        share_default = st.checkbox("Share Plaid imports with family", value=True, key="plaid_share_default")

        plaid_items = db_sidebar.query(PlaidItem).all()
        if plaid_items:
            for item in plaid_items:
                last_sync = item.last_synced_at.strftime("%b %d, %Y %I:%M %p") if item.last_synced_at else "Never"
                col_a, col_b = st.columns([2, 1])
                col_a.markdown(f"**{item.institution_name}**  \
Last sync: {last_sync}")
                if col_b.button("Sync now", key=f"sync_{item.id}"):
                    with st.spinner("Syncing transactions..."):
                        try:
                            new_count = sync_plaid_transactions(item, share_with_family=share_default)
                            st.success(f"Pulled {new_count} new transactions.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Plaid sync failed: {e}")
        else:
            st.caption("No banks linked yet.")

        st.markdown("---")
        st.markdown("**Link a new bank**")

        if st.button("🔗 Start Plaid Link (Sandbox)"):
            try:
                link_token = create_link_token(str(st.session_state.get("user_id", "admin")))
                st.info(f"Link Token Created: `{link_token}`")
                st.markdown("""
                1. Open `plaid_test.html` (in this repo) and paste the token above.
                2. Complete the flow to obtain a **Public Token**.
                3. Enter it below to save the connection.
                """)
            except Exception as e:
                st.error(f"Plaid Error: {e}")

        institution_label = st.text_input("Institution label", value="Plaid Sandbox")
        public_token = st.text_input("Public Token (from Plaid Link)", key="plaid_public_token")
        if st.button("Exchange & Save Connection", use_container_width=True) and public_token:
            try:
                access_token, item_id = exchange_public_token(public_token)
                plaid_item = upsert_plaid_item(item_id, access_token, institution_label)
                st.success(f"Saved connection for {plaid_item.institution_name}. You can sync immediately.")
            except Exception as e:
                st.error(f"Exchange Error: {e}")

    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["preview_as_family"] = False
        st.session_state["role"] = None
        st.session_state["user_id"] = None
        st.rerun()

# Load Data
df = load_data()
if not df.empty:
    df_prep = _prep(df)
else:
    df_prep = pd.DataFrame()

db_session = get_db()
budgets_all = db_session.query(CategoryBudget).all()
visible_budgets = [b for b in budgets_all if is_admin() or b.is_shared]
budget_status = compute_budget_status(df_prep, visible_budgets)

# Tabs (removed Connect tab - moved to sidebar)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Dashboard", "💳 Transactions", "💸 Loans", "📅 Fixed Expenses", "🧠 Insights", "📈 Net Worth"])

with tab6:
    st.header("📈 Net Worth History")
    
    db = get_db()
    
    # Calculate Current Net Worth
    # Assets: Sum of positive balances (simplified: sum of all positive transactions + manual assets if we had them)
    # For now, let's assume Assets = Sum of all Income - Sum of all Expenses (Cash Flow) + Initial Balance (0)
    # A better way for a simple tracker: Assets = Sum of all positive transactions? No, that's income.
    # Let's define Assets as: Sum of all transactions (Cash on Hand)
    # Liabilities: Sum of all Loan Balances
    
    # 1. Cash on Hand (Assets)
    all_txns = db.query(Transaction).all()
    cash_on_hand = sum(t.amount for t in all_txns)
    
    # 2. Liabilities
    all_loans = db.query(Loan).all()
    total_liabilities = sum(l.balance for l in all_loans)
    
    current_net_worth = cash_on_hand - total_liabilities
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Assets (Cash)", f"${cash_on_hand:,.2f}")
    col2.metric("Total Liabilities (Debt)", f"${total_liabilities:,.2f}", delta_color="inverse")
    col3.metric("Net Worth", f"${current_net_worth:,.2f}")
    
    st.divider()
    
    # Capture Snapshot
    if is_admin():
        if st.button("📸 Capture Today's Snapshot"):
            today = datetime.now().date()
            existing = db.query(NetWorthSnapshot).filter(NetWorthSnapshot.date == today).first()
            if existing:
                existing.total_assets = cash_on_hand
                existing.total_liabilities = total_liabilities
                existing.net_worth = current_net_worth
                st.success("Updated today's snapshot!")
            else:
                snap = NetWorthSnapshot(date=today, total_assets=cash_on_hand, total_liabilities=total_liabilities, net_worth=current_net_worth)
                db.add(snap)
                st.success("Captured new snapshot!")
            db.commit()
            st.rerun()
            
    # History Chart
    snapshots = db.query(NetWorthSnapshot).order_by(NetWorthSnapshot.date).all()
    if snapshots:
        data = [{
            "Date": s.date,
            "Net Worth": s.net_worth,
            "Assets": s.total_assets,
            "Liabilities": s.total_liabilities
        } for s in snapshots]
        df_nw = pd.DataFrame(data)
        
        fig = px.area(df_nw, x="Date", y="Net Worth", title="Net Worth Trend", markers=True)
        fig.add_scatter(x=df_nw["Date"], y=df_nw["Assets"], mode='lines', name='Assets', line=dict(dash='dot', color='green'))
        fig.add_scatter(x=df_nw["Date"], y=df_nw["Liabilities"], mode='lines', name='Liabilities', line=dict(dash='dot', color='red'))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No snapshots yet. Click 'Capture' to start tracking your history.")

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

        st.dataframe(df_exp.style.map(color_priority, subset=['Priority']), use_container_width=True)
        
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

    st.subheader("🎯 Category Budgets")
    existing_categories = sorted(df["Category"].unique().tolist()) if not df.empty else []

    if is_admin():
        with st.expander("➕ Add or Update Budget"):
            with st.form("add_budget"):
                choice = st.selectbox("Use an existing category", ["Type a new one"] + existing_categories)
                custom = st.text_input("Or type a new category")
                category_val = custom.strip() or (choice if choice != "Type a new one" else "")
                limit = st.number_input("Monthly limit ($)", min_value=0.0, step=50.0)
                share_budget = st.checkbox("Share this budget with family", value=True)

                if st.form_submit_button("Save Budget"):
                    if not category_val:
                        st.error("Please choose or enter a category.")
                    else:
                        existing_budget = db.query(CategoryBudget).filter(CategoryBudget.category == category_val).first()
                        if existing_budget:
                            existing_budget.monthly_limit = limit
                            existing_budget.is_shared = share_budget
                        else:
                            db.add(CategoryBudget(category=category_val, monthly_limit=limit, is_shared=share_budget))
                        db.commit()
                        st.success(f"Budget saved for {category_val}.")
                        st.rerun()

    if visible_budgets:
        budget_data = [{
            "Category": b.category,
            "Monthly Limit": b.monthly_limit,
            "Shared": b.is_shared
        } for b in visible_budgets]
        st.dataframe(pd.DataFrame(budget_data), use_container_width=True)
    else:
        st.info("No budgets configured yet.")


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

        if budget_status:
            st.subheader("🎯 Budgets (This Month)")
            for b in budget_status:
                remaining = b["remaining"]
                status_label = "On track" if remaining >= 0 else "Over budget"
                st.markdown(f"**{b['category']}** — ${b['spent']:,.0f} / ${b['limit']:,.0f} ({status_label})")
                st.progress(min(1.0, b["pct"]), text=f"Spent ${b['spent']:,.0f} • Remaining ${max(0, remaining):,.0f}")
                if b["is_over"]:
                    st.error(f"Over by ${abs(remaining):,.0f}. Consider pausing discretionary spend here.")

with tab2:
    st.subheader("Transaction Log")
    if budget_status:
        over_budget = [b for b in budget_status if b["is_over"]]
        for b in over_budget:
            st.warning(f"{b['category']} is over budget by ${abs(b['remaining']):,.0f}. Recent transactions in this category deserve a closer look.")
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

        extra_pmt = st.slider("Extra Monthly Payment ($)", 0, 2000, 0, help="Add a top-up to your required payment to see the impact.")

        base_schedule = simulate_payoff(selected_loan.balance, selected_loan.interest_rate, selected_loan.min_payment, extra_payment=0)
        boosted_schedule = simulate_payoff(selected_loan.balance, selected_loan.interest_rate, selected_loan.min_payment, extra_payment=extra_pmt)

        if base_schedule.empty:
            st.error("The current payment is too low to cover interest. Increase the minimum payment to see a schedule.")
        else:
            months_base = len(base_schedule)
            months_boost = len(boosted_schedule) if not boosted_schedule.empty else months_base
            interest_base = base_schedule["Interest"].sum()
            interest_boost = boosted_schedule["Interest"].sum() if not boosted_schedule.empty else interest_base

            years_base = months_base // 12
            years_boost = months_boost // 12

            c1, c2, c3 = st.columns(3)
            c1.metric("Payoff (minimums)", f"{years_base}y {months_base % 12}m")
            if extra_pmt > 0 and not boosted_schedule.empty:
                c2.metric("Payoff with extra", f"{years_boost}y {months_boost % 12}m", delta=f"-{months_base - months_boost} months")
                c3.metric("Interest saved", f"${interest_base - interest_boost:,.0f}")
            else:
                c2.metric("Extra payment", "$0", help="Move the slider to compare scenarios.")
                c3.metric("Interest (minimums)", f"${interest_base:,.0f}")

            # Chart both curves
            chart_df = pd.DataFrame({
                "Month": base_schedule["Month"],
                "Balance (Minimum)": base_schedule["Balance"]
            })
            if not boosted_schedule.empty:
                chart_df["Balance (With Extra)"] = boosted_schedule["Balance"]
            st.line_chart(chart_df.set_index("Month"))
            st.caption("The chart compares how quickly the balance falls with and without the extra payment.")

            with st.expander("See amortization table"):
                preview_rows = boosted_schedule if not boosted_schedule.empty else base_schedule
                st.dataframe(preview_rows.head(24), use_container_width=True)

    else:
        st.info("No loans found.")

with tab5:
    st.header("🧠 Smart Insights")

    if df_prep.empty:
        st.info("Need transaction data to generate insights.")
    else:
        st.caption("Curated highlights, budget watch-outs, and an on-page assistant to make this page actually smart.")

        col_range, _ = st.columns([3, 1])
        with col_range:
            window_label = st.selectbox(
                "Timeframe",
                ["Last 90 days", "Last 180 days", "Year to date", "All data"],
                index=1,
                help="Insights will be generated from this window."
            )

        filtered_df = df_prep.copy()
        cutoff = None
        today = filtered_df["Date"].max()
        if window_label == "Last 90 days":
            cutoff = today - pd.Timedelta(days=90)
        elif window_label == "Last 180 days":
            cutoff = today - pd.Timedelta(days=180)
        elif window_label == "Year to date":
            cutoff = pd.Timestamp(pd.Timestamp.today().year, 1, 1)

        if cutoff:
            filtered_df = filtered_df[filtered_df["Date"] >= cutoff]

        if filtered_df.empty:
            st.info("No data in the selected window. Try expanding the timeframe.")
            st.stop()

        highlights = compute_highlights(filtered_df)
        st.subheader("Highlights")
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Income", f"${highlights['income']:,.0f}", help=f"Latest month: {highlights['month']}")
        h2.metric("Spend", f"${highlights['spend']:,.0f}")
        h3.metric("Net Cashflow", f"${highlights['net']:,.0f}", delta_color="normal")
        top_cat = highlights.get("top_category") or "—"
        top_val = highlights.get("top_category_spend", 0)
        h4.metric("Top Category", top_cat, delta=f"-${top_val:,.0f}" if top_cat != "—" else None)

        st.subheader("Actionable Tips")
        tips = generate_actionable_tips(filtered_df)
        if tips:
            for tip in tips:
                st.markdown(
                    f"""
                    <div style="padding:15px; background-color:#f8fafc; border-radius:10px; margin-bottom:10px; border:1px solid #e2e8f0">{tip}</div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("✅ Your finances look stable! No alerts this month.")

        st.subheader("Anomalies & Unusual Activity")
        anomalies = detect_anomalies(filtered_df)
        if not anomalies.empty:
            show_cols = ["Date", "Description", "Amount", "Category"]
            st.dataframe(anomalies[show_cols].assign(Amount=anomalies["Amount"].abs()), use_container_width=True)
            st.caption("Transactions more than 2 standard deviations from your normal spend.")
        else:
            st.info("No suspicious spikes detected in the selected window.")

        st.subheader("Budget Watch")
        budget_alerts = summarize_budget_watch(budget_status)
        if budget_alerts:
            for alert in budget_alerts:
                st.warning(alert)
        else:
            st.success("No budgets are at risk right now.")

        st.subheader("🔮 Spending Forecast")
        forecast = predict_spending(filtered_df)
        st.plotly_chart(forecast["figure"], use_container_width=True)
        st.caption(forecast.get("summary", ""))
        if forecast.get("forecast_month"):
            st.caption(f"Next update based on data through {forecast['forecast_month']} (refreshed {forecast['updated_at']:%Y-%m-%d %H:%M UTC}).")

        st.subheader("💬 AI Insights Assistant")
        with st.form("insights_assistant"):
            prompt = st.text_area(
                "Ask a question about your money",
                placeholder="e.g., Where can I trim spend this month?",
                help="Uses on-page data only; no external calls."
            )
            submitted = st.form_submit_button("Ask the Assistant")

        if submitted:
            response = assistant_response(filtered_df, prompt, budget_status, forecast, anomalies)
            formatted_response = response.replace("\n", "<br>")
            st.markdown(
                f"""
                <div style="padding:15px; background-color:#eef2ff; border-radius:10px; border:1px solid #c7d2fe">
                    {formatted_response}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("Try asking: • What changed most this month? • How do I avoid overspending this week? • Where is my biggest category drift?")
