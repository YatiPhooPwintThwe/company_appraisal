# seed_db.py
import csv
import os
from datetime import datetime

from app import app
from models import db, User
from extensions import bcrypt

CSV_FILENAME = os.path.join(os.path.dirname(__file__), "employees.csv")  # change if name different



def create_user_from_row(row):
    """
    CSV columns:
    employee_id,name,password,role,position,department,avatar,email
    """
    employee_id = row["employee_id"].strip()
    name = row["name"].strip()
    password = row["password"].strip()
    role = row["role"].strip()
    position = row["position"].strip()
    department = row["department"].strip()
    avatar = row["avatar"].strip()
    email = row["email"].strip()

    # check duplicates by login_id
    existing = User.query.filter_by(login_id=employee_id).first()
    if existing:
        print(f"User {employee_id} exists — skipping.")
        return

    user = User(
        login_id=employee_id,
        name=name,
        password=password,
        role=role,
        position=position,
        department=department,
        avatar_url=avatar,
        email=email,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.session.add(user)
    print(f"Added user {employee_id} - {name}")


def main():
    if not os.path.exists(CSV_FILENAME):
        print(f"CSV not found: {CSV_FILENAME}")
        return

    with app.app_context():
        with open(CSV_FILENAME, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    create_user_from_row(row)
                except Exception as e:
                    print("Row failed:", row, "Error:", e)

        try:
            db.session.commit()
            print("Seeding completed successfully.")
        except Exception as e:
            db.session.rollback()
            print("Commit failed:", e)


if __name__ == "__main__":
    main()
