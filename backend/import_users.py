import csv
import os
from datetime import datetime
from app import app, db
from models import User

CSV_FILE = "employees.csv"
AVATAR_FOLDER = "statics/profile"

def import_users():
    with app.app_context():
        db.create_all()

        # **Delete all existing users first**
        deleted = User.query.delete()
        db.session.commit()
        print(f"Deleted {deleted} existing users.")

        users_to_add = []

        try:
            with open(CSV_FILE, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    user = User(
                        login_id=row['employee_id'],
                        name=row['name'],
                        password=row['password'],  # plain text
                        role=row['role'],
                        position=row.get('position'),
                        department=row.get('department'),
                        avatar_url=os.path.join(AVATAR_FOLDER, row['avatar']).replace("\\", "/"),
                        email=row['email'],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    users_to_add.append(user)
                    print(f"Added user {row['employee_id']} - {row['name']}")

            if users_to_add:
                db.session.add_all(users_to_add)
                db.session.commit()
                print(f"Successfully imported {len(users_to_add)} users.")

        except FileNotFoundError:
            print(f"CSV file not found: {CSV_FILE}")
        except Exception as e:
            db.session.rollback()
            print("Error during import:", e)

if __name__ == "__main__":
    import_users()
