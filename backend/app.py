import os
import sys

# Ensure the 'backend' directory is in the Python path for Vercel
sys.path.append(os.path.dirname(__file__))

from flask import Flask, jsonify
from flask_cors import CORS
from database import init_firebase_admin
from auth import auth_bp
from services import services_bp
from chatbot import chatbot_bp

def create_app() -> Flask:
    app = Flask(__name__)
    
    # Allow all origins and common headers for local development and Vercel
    CORS(app, resources={r"/*": {"origins": "*"}}, 
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

    # Initialize Firebase Admin SDK
    init_firebase_admin()

    # Register Blueprints with explicit prefixes to match frontend calls and Vercel routing
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(services_bp, url_prefix='/api/services')
    app.register_blueprint(chatbot_bp, url_prefix='/api')

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "app": "MCDM API"})

    @app.errorhandler(404)
    def not_found(e): 
        return jsonify({"status": "error", "message": "Not found."}), 404

    @app.errorhandler(500)
    def server_error(e): 
        return jsonify({"status": "error", "message": "Internal error."}), 500

    return app

# Expose 'app' for Vercel
app = create_app()
