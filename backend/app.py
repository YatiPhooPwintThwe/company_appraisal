from flask import Flask, send_from_directory, jsonify
from extensions import db, bcrypt 
from flask_cors import CORS
import os
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
import cloudinary
import cloudinary.uploader
import cloudinary.api

load_dotenv()

app = Flask(
    __name__,
    static_folder="frontend_dist",
    static_url_path=""
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

# --- register API routes first ---
from routes import register_routes
PERSPECTIVE_API_KEY = os.getenv("PERSPECTIVE_API_KEY")
register_routes(app, db=db, PERSPECTIVE_API_KEY=PERSPECTIVE_API_KEY)

@app.route("/login", methods=["GET"])
def login_page():
    return send_from_directory(app.static_folder, "index.html")

# --- catch-all for React frontend ---
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    # Only serve React for non-API routes
    api_prefixes = ["login", "users", "posts", "replies", "polls", "notifications"]
    if any(path.startswith(p) for p in api_prefixes):
        return jsonify({"error": "Not found"}), 404

    # Serve static files if they exist
    file_path = os.path.join(app.static_folder, path)
    if path and os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)

    # Default: serve index.html
    return send_from_directory(app.static_folder, "index.html")






