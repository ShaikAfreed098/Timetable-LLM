import argparse
import logging
import sys

from app.database import SessionLocal
from app.models.institution import Institution
from app.models.user import User
from app.models.config import ScheduleConfig
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)

def bootstrap(args):
    db = SessionLocal()
    try:
        # Check if institution already exists
        existing_inst = db.query(Institution).filter(
            (Institution.slug == args.slug) | (Institution.name == args.institution_name)
        ).first()
        if existing_inst:
            print(f"Error: Institution with name '{args.institution_name}' or slug '{args.slug}' already exists.")
            sys.exit(1)

        # Check if user already exists
        existing_user = db.query(User).filter(User.email == args.admin_email).first()
        if existing_user:
            print(f"Error: User with email '{args.admin_email}' already exists.")
            sys.exit(1)

        print(f"Creating institution: {args.institution_name}")
        inst = Institution(
            name=args.institution_name,
            slug=args.slug,
            grouping_scheme="batch",
            is_active=True
        )
        db.add(inst)
        db.flush()  # To get the ID

        print("Creating default schedule config (Mon-Fri, 7 periods)")
        config = ScheduleConfig(
            institution_id=inst.id,
            working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            periods_per_day=7,
            period_times={
                "1": "09:00-09:50",
                "2": "09:50-10:40",
                "3": "10:50-11:40",
                "4": "11:40-12:30",
                "5": "13:30-14:20",
                "6": "14:20-15:10",
                "7": "15:20-16:10",
            }
        )
        db.add(config)

        print(f"Creating super_admin user: {args.admin_email}")
        hashed_password = pwd_context.hash(args.admin_password)
        username = args.admin_email.split("@")[0]
        # Make sure username is unique
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            username = f"{username}_{inst.slug}"
            
        user = User(
            institution_id=inst.id,
            username=username,
            email=args.admin_email,
            hashed_password=hashed_password,
            role="super_admin",
        )
        db.add(user)

        db.commit()
        print("Bootstrap complete!")
    except Exception as e:
        db.rollback()
        print(f"Error during bootstrap: {e}")
        sys.exit(1)
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Timetable-LLM Admin CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # bootstrap
    boot_parser = subparsers.add_parser("bootstrap", help="Create the first institution and super admin user.")
    boot_parser.add_argument("--institution-name", required=True, help="Name of the institution")
    boot_parser.add_argument("--slug", required=True, help="Short slug for the institution (e.g. mit)")
    boot_parser.add_argument("--admin-email", required=True, help="Email address of the super admin")
    boot_parser.add_argument("--admin-password", required=True, help="Password for the super admin")

    args = parser.parse_args()

    if args.command == "bootstrap":
        bootstrap(args)

if __name__ == "__main__":
    main()
