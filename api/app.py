"""
app.py — Flask application factory and entry point for Vercel.
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from database import (
    init_firebase_admin, 
    build_service_record, 
    add_service_to_db, 
    get_services_from_db, 
    delete_service_from_db, 
    delete_all_services_from_db, 
    update_service_in_db,
    verify_id_token,
    SERVICE_ALL_FIELDS,
    SERVICE_NUMERIC_FIELDS
)
from auth import auth_bp
from services import services_bp, success_response, error_response
from algorithm import run_ranking

def create_app() -> Flask:
    app = Flask(__name__)
    
    # Allow all origins
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # Initialize Firebase Admin SDK
    init_firebase_admin()

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(services_bp)

    # --- Internal auth helper ---
    def _require_auth():
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None, error_response("Authorization header missing or malformed.", 401)
        try:
            decoded = verify_id_token(header.split("Bearer ")[1].strip())
            return decoded["uid"], None
        except Exception as e:
            return None, error_response(f"Invalid or expired token: {e}", 401)

    # --- Root Routes (Merged from db_routes) ---
    @app.route("/add_service", methods=["POST"])
    def add_service():
        uid, err = _require_auth()
        if err: return err
        body = request.get_json(silent=True)
        if not body: return error_response("Request body must be JSON.", 400)
        try:
            record = build_service_record(body)
            existing_services = get_services_from_db(uid)
            if any(s.get("service_name", "").lower() == record["service_name"].lower() for s in existing_services):
                return error_response("Service already exists in database", 409)
            stored = add_service_to_db(uid, record)
            return success_response(data=stored, message=f"Service '{record['service_name']}' added.", status=201)
        except Exception as e:
            return error_response(str(e), 500)

    @app.route("/get_services", methods=["GET"])
    def get_services():
        uid, err = _require_auth()
        if err: return err
        try:
            services = get_services_from_db(uid)
            search = request.args.get("search", "").strip().lower()
            if search:
                services = [s for s in services if search in s.get("service_name", "").lower()]
            
            sort_by = request.args.get("sort_by", "timestamp")
            order = request.args.get("order", "desc").lower()
            reverse = (order == "desc")
            services.sort(key=lambda s: s.get(sort_by) or (0 if sort_by != "service_name" else ""), reverse=reverse)

            total_count = len(services)
            limit = int(request.args.get("limit", 10))
            page = int(request.args.get("page", 1))
            start_idx = (page - 1) * limit
            
            avg_rt = round(sum(s.get("response_time", 0) for s in services) / total_count, 2) if total_count > 0 else 0
            avg_tp = round(sum(s.get("throughput", 0) for s in services) / total_count, 2) if total_count > 0 else 0
            
            return success_response(data={
                "count": total_count,
                "avg_response_time": avg_rt,
                "avg_throughput": avg_tp,
                "page": page,
                "limit": limit,
                "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1,
                "services": services[start_idx : start_idx + limit]
            })
        except Exception as e:
            return error_response(str(e), 500)

    @app.route("/delete_service/<service_id>", methods=["DELETE"])
    def delete_service(service_id: str):
        uid, err = _require_auth()
        if err: return err
        try:
            if delete_service_from_db(uid, service_id):
                return success_response(message="Service deleted.")
            return error_response("Service not found.", 404)
        except Exception as e:
            return error_response(str(e), 500)

    @app.route("/update_service/<service_id>", methods=["PUT"])
    def update_service(service_id: str):
        uid, err = _require_auth()
        if err: return err
        body = request.get_json(silent=True)
        if not body: return error_response("Request body must be JSON.", 400)
        updates = {}
        for field in SERVICE_NUMERIC_FIELDS:
            if field in body:
                try: updates[field] = float(body[field])
                except: return error_response(f"Field '{field}' must be a number.", 400)
        
        if not updates: return error_response("No valid fields to update.", 400)
        try:
            updated = update_service_in_db(uid, service_id, updates)
            return success_response(data=updated, message="Service updated.")
        except Exception as e:
            return error_response(str(e), 500)

    @app.route("/delete_all_services", methods=["DELETE"])
    def delete_all_services():
        uid, err = _require_auth()
        if err: return err
        try:
            delete_all_services_from_db(uid)
            return success_response(message="All services deleted.")
        except Exception as e:
            return error_response(str(e), 500)

    @app.route("/rank_services", methods=["POST", "OPTIONS"])
    def rank_services_root():
        if request.method == "OPTIONS": return jsonify({}), 200
        uid, err = _require_auth()
        if err: return err
        try:
            services = get_services_from_db(uid)
            if len(services) < 2: return error_response("At least 2 services are needed to rank.", 400)
            result_df, weights, criteria = run_ranking(services)
            return success_response(data={
                "ranked": result_df.to_dict(orient="records"),
                "weights": {c: round(float(w), 6) for c, w in zip(criteria, weights)},
                "criteria": criteria,
                "best": result_df.iloc[0]["service_name"],
            }, message="Ranking computed.")
        except Exception as e:
            return error_response(str(e), 500)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "app": "MCDM API"})

    @app.errorhandler(404)
    def not_found(e): return jsonify({"status": "error", "message": "Not found."}), 404

    @app.errorhandler(500)
    def server_error(e): return jsonify({"status": "error", "message": "Internal error."}), 500

    return app

# Expose 'app' for Vercel
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("FLASK_PORT", 5000)), debug=True)
