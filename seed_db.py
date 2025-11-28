import bcrypt
from database import init_db, SessionLocal, User

def seed_users():
    init_db()
    db = SessionLocal()
    
    # Check if users exist
    if db.query(User).first():
        print("Users already exist. Skipping seed.")
        db.close()
        return

    # Admin User
    admin_pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode('utf-8')
    admin = User(username="admin", password_hash=admin_pw, role="admin")
    
    # Family User (Brother)
    family_pw = bcrypt.hashpw(b"brother123", bcrypt.gensalt()).decode('utf-8')
    family = User(username="brother", password_hash=family_pw, role="family")
    
    db.add(admin)
    db.add(family)
    db.commit()
    print("Database initialized with default users.")
    db.close()

if __name__ == "__main__":
    seed_users()
