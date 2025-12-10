import os
from datetime import datetime, timezone
from app import app, db
from models import User

# Hardcoded user data
users = [
    {"login_id":"A001","name":"Emma Tan","password":"Admin@123","role":"admin","position":"HR Manager","department":"Human Resources","avatar":"female.png","email":"emma.tan@abcdabcdcompany.com"},
    {"login_id":"A002","name":"Jason Lim","password":"Admin@456","role":"admin","position":"System Administrator","department":"IT","avatar":"male.jpg","email":"jason.lim@abcdabcdcompany.com"},
    {"login_id":"E101","name":"Aung Ko","password":"Emp@101","role":"employee","position":"Software Engineer","department":"IT","avatar":"male.jpg","email":"aung.ko@abcdabcdcompany.com"},
    {"login_id":"E102","name":"Mary Soo","password":"Emp@102","role":"employee","position":"UI/UX Designer","department":"Design","avatar":"female.png","email":"mary.soo@abcdabcdcompany.com"},
    {"login_id":"E103","name":"John Lee","password":"Emp@103","role":"employee","position":"Backend Developer","department":"IT","avatar":"male.jpg","email":"john.lee@abcdabcdcompany.com"},
    {"login_id":"E104","name":"Michelle Yeo","password":"Emp@104","role":"employee","position":"Frontend Developer","department":"IT","avatar":"female.png","email":"michelle.yeo@abcdabcdcompany.com"},
    {"login_id":"E105","name":"Nathan Goh","password":"Emp@105","role":"employee","position":"QA Tester","department":"Quality Assurance","avatar":"male.jpg","email":"nathan.goh@abcdabcdcompany.com"},
    {"login_id":"E106","name":"Sophie Chan","password":"Emp@106","role":"employee","position":"Project Manager","department":"Management","avatar":"female.png","email":"sophie.chan@abcdabcdcompany.com"},
    {"login_id":"E107","name":"Daniel Tan","password":"Emp@107","role":"employee","position":"DevOps Engineer","department":"IT","avatar":"male.jpg","email":"daniel.tan@abcdabcdcompany.com"},
    {"login_id":"E108","name":"Grace Wong","password":"Emp@108","role":"employee","position":"Marketing Executive","department":"Marketing","avatar":"female.png","email":"grace.wong@abcdabcdcompany.com"},
    {"login_id":"E109","name":"Benjamin Ho","password":"Emp@109","role":"employee","position":"Content Writer","department":"Marketing","avatar":"male.jpg","email":"benjamin.ho@abcdabcdcompany.com"},
    {"login_id":"E110","name":"Karen Lu","password":"Emp@110","role":"employee","position":"Finance Officer","department":"Finance","avatar":"female.png","email":"karen.lu@abcdcompany.com"},
    {"login_id":"E111","name":"Lucas Chua","password":"Emp@111","role":"employee","position":"Data Analyst","department":"Data","avatar":"male.jpg","email":"lucas.chua@abcdcompany.com"},
    {"login_id":"E112","name":"Elena Park","password":"Emp@112","role":"employee","position":"HR Executive","department":"Human Resources","avatar":"female.png","email":"elena.park@abcdcompany.com"},
    {"login_id":"E113","name":"Ryan Phyo","password":"Emp@113","role":"employee","position":"Support Engineer","department":"Support","avatar":"male.jpg","email":"ryan.phyo01@abcdcompany.com"},
    {"login_id":"E114","name":"Ryan Phyo","password":"Emp@114","role":"employee","position":"Support Engineer","department":"Support","avatar":"male.jpg","email":"ryan.phyo02@abcdcompany.com"}
]

AVATAR_FOLDER = "statics/profile"

def seed_users():
    with app.app_context():
        db.create_all()

        # Delete existing users
        print("Deleting existing users...")
        num_deleted = db.session.query(User).delete()
        db.session.commit()
        print(f"Deleted {num_deleted} users.")

        # Add new users
        for u in users:
            user = User(
                login_id=u["login_id"],
                name=u["name"],
                password=u["password"],  # plain text
                role=u["role"],
                position=u.get("position"),
                department=u.get("department"),
                avatar_url=os.path.join(AVATAR_FOLDER, u["avatar"]).replace("\\", "/") if u.get("avatar") else None,
                email=u.get("email"),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.session.add(user)
            print(f"Added user {u['login_id']} - {u['name']}")

        db.session.commit()
        print(f"Successfully imported {len(users)} users.")

if __name__ == "__main__":
    seed_users()
