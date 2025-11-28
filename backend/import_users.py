import csv
import os
from app import app, db
from models import User

CSV_FILE = 'employees.csv'
AVATAR_FOLDER = 'statics/profile'

def import_users():
    users_to_add = []

    with app.app_context():
        print("Starting database import...")
        db.create_all()

        try:
            with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if not all(row.get(field) for field in ['employee_id', 'name', 'password', 'role', 'avatar']):
                        print(f"Skipping row due to missing required data: {row}")
                        continue

                    if User.query.filter_by(login_id=row['employee_id']).first():
                        print(f"User {row['employee_id']} already exists, skipping.")
                        continue

                    new_user = User(
                        login_id=row['employee_id'],
                        name=row['name'],
                        role=row['role'],
                        position=row.get('position'),
                        department=row.get('department'),
                        avatar_url=os.path.join(AVATAR_FOLDER, row['avatar']).replace("\\", "/"),
                        email=row['email'] 

                    )
                    new_user.set_password(row['password'])
                    users_to_add.append(new_user)

            if users_to_add:
                db.session.add_all(users_to_add)
                db.session.commit()
                print(f"Successfully imported {len(users_to_add)} users.")
            else:
                print("No new users to import.")

        except FileNotFoundError:
            print(f"ERROR: File '{CSV_FILE}' not found.")
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred during import: {str(e)}")

if __name__ == '__main__':
    import_users()
