import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.core.auth import get_password_hash

def create_super_admin():
    db = SessionLocal()
    # Check if admin exists
    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        print("Admin user already exists.")
        return

    hashed_pw = get_password_hash("admin123")
    new_admin = User(
        username="admin",
        email="admin@college.edu",
        hashed_password=hashed_pw,
        role="super_admin",
        is_active=True
    )
    db.add(new_admin)
    db.commit()
    print("Super Admin user created successfully! Username: admin, Password: admin123")

if __name__ == "__main__":
    create_super_admin()
