import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Setup
# Default to local SQLite, but allow override for AWS RDS (Postgres)
DB_URL = os.getenv("DATABASE_URL", "sqlite:///finance_tracker.db")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String) # Store bcrypt hash, not plain text
    role = Column(String) # 'admin' or 'family'

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    description = Column(String)
    amount = Column(Float)
    category = Column(String)
    
    # Intelligence & Workflow
    confidence_score = Column(Float, default=1.0) # 0.0 to 1.0
    is_reviewed = Column(Boolean, default=True)   # False if low confidence
    
    # Sharing & Access Control
    is_shared = Column(Boolean, default=False)    # True if visible to 'family' role
    
    # Metadata
    source = Column(String, default="manual")     # 'manual', 'plaid', 'csv_upload'
    plaid_transaction_id = Column(String, unique=True, nullable=True)

class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    lender = Column(String)
    loan_type = Column(String)
    principal = Column(Float)
    balance = Column(Float)
    interest_rate = Column(Float)
    min_payment = Column(Float)
    term_months = Column(Integer)
    
    # Sharing
    is_shared = Column(Boolean, default=False)

class FixedExpense(Base):
    __tablename__ = "fixed_expenses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    amount = Column(Float)
    due_date = Column(Integer) # Day of month (1-31)
    category = Column(String)
    priority = Column(String) # 'Critical', 'High', 'Medium', 'Low'
    is_shared = Column(Boolean, default=False)

# --- Init DB ---
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
