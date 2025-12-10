from flask import Flask, send_from_directory
from extensions import db, bcrypt 
from flask_cors import CORS
import os
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_migrate import Migrate
import cloudinary
import cloudinary.uploader
import cloudinary.api

load_dotenv()

# --- setup app ---
app = Flask(
    __name__,
    static_folder="statics",     # folder on disk: backend/statics
    static_url_path="/statics"   # served at http(s)://<host>:<port>/statics/...
)

CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///employees.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_TOKEN_KEY")
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)

frontend_folder = os.path.join(os.getcwd(),"..","frontend")
dist_folder = os.path.join(frontend_folder,"dist")
@app.route("/", defaults={"filename": ""})
@app.route("/<path:filename>")
def index(filename):
    file_path = os.path.join(dist_folder, filename)
    if os.path.exists(file_path):
        return send_from_directory(dist_folder, filename)
    # fallback to index.html for SPA
    return send_from_directory(dist_folder, "index.html")

# Perspective API key
PERSPECTIVE_API_KEY = os.getenv("PERSPECTIVE_API_KEY")

# --- register routes ---
from routes import register_routes
register_routes(app, db=db, PERSPECTIVE_API_KEY=PERSPECTIVE_API_KEY)


