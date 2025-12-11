from flask import Flask, send_from_directory, jsonify, request
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

# --- Config ---
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

# --- Init extensions ---
db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)



# --- Register API routes ---
from routes import register_routes
PERSPECTIVE_API_KEY = os.getenv("PERSPECTIVE_API_KEY")
register_routes(app, db=db, PERSPECTIVE_API_KEY=PERSPECTIVE_API_KEY)

# --- Serve React login page ---
@app.route("/login", methods=["GET"])
def login_page():
    return send_from_directory(app.static_folder, "index.html")

# --- Catch-all for React frontend (only GET requests) ---
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if request.method != "GET":
        # let POST/PUT/DELETE to API routes work normally
        return jsonify({"error": "Method not allowed"}), 405

    # Do not serve React for API paths
    api_prefixes = ["users", "posts", "replies", "polls", "notifications", "login"]
    if any(path.startswith(p) for p in api_prefixes):
        return jsonify({"error": "Not found"}), 404

    # Serve static files if they exist
    file_path = os.path.join(app.static_folder, path)
    if path and os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)

    # Default: serve index.html
    return send_from_directory(app.static_folder, "index.html")


@app.route("/statics/<path:filename>")
def serve_statics(filename):
    return send_from_directory("backend/statics", filename)
if __name__ == "__main__":
    app.run(debug=True, port=5000)
