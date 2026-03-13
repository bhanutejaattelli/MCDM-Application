"""
app.py — Flask application factory and entry point for Vercel.
"""
from flask import Flask, jsonify
from flask_cors import CORS
from database import init_firebase_admin
from auth import auth_bp
from services import services_bp

def create_app() -> Flask:
    app = Flask(__name__)
    
    # Allow all origins
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # Initialize Firebase Admin SDK
    init_firebase_admin()

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(services_bp)

    @app.route("/health", methods=["GET"])
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
