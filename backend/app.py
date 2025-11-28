from flask import Flask
from extensions import db, bcrypt 
from flask_cors import CORS
import os
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_migrate import Migrate

load_dotenv()

# --- setup app ---
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///employees.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_TOKEN_KEY")

db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)

# Perspective API key
PERSPECTIVE_API_KEY = os.getenv("PERSPECTIVE_API_KEY")

# --- register routes ---
from routes import register_routes
register_routes(app, db=db, PERSPECTIVE_API_KEY=PERSPECTIVE_API_KEY)

@app.route("/")
def hello_world():
    
    return "<h1>Hello, CompanyAppraisal!</h1>"


if __name__ == "__main__":
    app.run(debug=True)
