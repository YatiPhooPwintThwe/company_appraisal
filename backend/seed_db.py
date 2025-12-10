import csv
import os
from datetime import datetime, timezone

from app import app, db
from models import User

# CSV file containing user data
CSV_FILE = os.path.join(os.path.dirname(__file__), "employees.csv")
AVATAR_FOLDER = "statics/profile"  # adjust if your avatars are stored elsewhere


def import_users():
    with app.app_context():
        # Ensure tables exist
        db.create_all()

        # Delete all existing users
        print("Deleting existing users...")
        num_deleted = db.session.query(User).delete()
        db.session.commit()
        print(f"Deleted {num_deleted} users.")

        # Import users from CSV
        users_to_add = []

        if not os.path.exists(CSV_FILE):
            print(f"CSV file not found: {CSV_FILE}")
            return

        with open(CSV_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    login_id = row["employee_id"].strip()
                    name = row["name"].strip()
                    password = row["password"].strip()  # plain text
                    role = row["role"].strip()
                    position = row.get("position")
                    department = row.get("department")
                    avatar = row.get("avatar")
                    email = row.get("email")

                    user = User(
                        login_id=login_id,
                        name=name,
                        password=password,
                        role=role,
                        position=position,
                        department=department,
                        avatar_url=os.path.join(AVATAR_FOLDER, avatar).replace("\\", "/") if avatar else None,
                        email=email,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    users_to_add.append(user)
                    print(f"Added user {login_id} - {name}")
                except Exception as e:
                    print(f"Failed to process row {row}: {e}")

        if users_to_add:
            db.session.add_all(users_to_add)
            db.session.commit()
            print(f"Successfully imported {len(users_to_add)} users.")
        else:
            print("No users were imported.")


if __name__ == "__main__":
    import_users()
