from database import engine, Base, FixedExpense

def migrate_db():
    print("Migrating database...")
    # This will create any missing tables (like fixed_expenses)
    Base.metadata.create_all(bind=engine)
    print("Migration complete!")

if __name__ == "__main__":
    migrate_db()
