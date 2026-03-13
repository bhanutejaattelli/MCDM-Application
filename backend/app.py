"""
app.py — Flask application factory and entry point.
Run: python backend/app.py
"""
from flask import Flask, jsonify
from flask_cors import CORS
from database import init_firebase_admin
import os
from auth import auth_bp
from services import services_bp


def create_app() -> Flask:
    app = Flask(__name__)
    
    # Allow all origins (React frontend on localhost:5173 / Streamlit on 8501)
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # Initialize Firebase Admin SDK
    init_firebase_admin()

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(services_bp)
    

    
    # --- DB ROUTES MIGRATED ---
    from database import build_service_record, add_service_to_db, get_services_from_db, delete_service_from_db, delete_all_services_from_db, SERVICE_ALL_FIELDS
    from database import verify_id_token
    from services import success_response, error_response
    from flask import request

    """
db_routes.py â€” Firebase Realtime Database API endpoints.

Dedicated Blueprint exposing the core service data routes:

  POST  /add_service      â†’ Validate + persist a single service to Firebase
  GET   /get_services     â†’ Retrieve all services for the authenticated user

Authentication: All routes require  Authorization: Bearer <idToken>

Service schema stored per entry in /services/{uid}/{push_id}/:
  service_name  : string
  response_time : float  (ms)
  throughput    : float  (req/s)
  security      : float  (0-100)
  cost          : float  (USD/mo)
  timestamp     : string (ISO-8601 UTC)
"""

    from database import (
    build_service_record,
    add_service_to_db,
    get_services_from_db,
    delete_service_from_db,
    delete_all_services_from_db,
    SERVICE_ALL_FIELDS,
)



# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Internal auth helper
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def _require_auth() -> tuple[str | None, object]:
    """
    Read the Bearer token from the Authorization header, verify it, return uid.
    Returns (uid, None) on success or (None, error_response) on failure.
    """
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, error_response(
            "Authorization header missing or malformed. "
            "Expected: Authorization: Bearer <idToken>", 401
        )
    try:
        decoded = verify_id_token(header.split("Bearer ")[1].strip())
        return decoded["uid"], None
    except Exception as e:
        return None, error_response(f"Invalid or expired token: {e}", 401)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# POST /add_service
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@app.route("/add_service", methods=["POST"])
def add_service():
    """
    Add a single cloud service to Firebase Realtime Database.

    Headers:
        Authorization: Bearer <idToken>
        Content-Type:  application/json

    Request body (JSON):
    {
        "service_name"  : "AWS EC2 t3.medium",   â† required
        "response_time" : 120.5,                  â† ms  (optional, default 0)
        "throughput"    : 850.0,                  â† req/s
        "security"      : 88.0,                   â† score 0-100
        "cost"          : 250.0,                  â† USD/month
        "timestamp"     : "2026-03-11T16:28:00Z" â† optional, auto-set if omitted
    }

    Success (201):
    {
        "status":  "success",
        "message": "Service 'AWS EC2 t3.medium' added successfully.",
        "data": {
            "id":           "-NxABC123...",
            "service_name": "AWS EC2 t3.medium",
            "response_time": 120.5,
            "throughput":    850.0,
            "security":      88.0,
            "cost":          250.0,
            "timestamp":    "2026-03-11T16:28:00Z"
        }
    }
    """
    uid, err = _require_auth()
    if err:
        return err

    body = request.get_json(silent=True)
    if not body:
        return error_response(
            "Request body must be JSON. "
            "Set Content-Type: application/json and send a JSON object.", 400
        )

    # Validate and normalise input â†’ canonical DB record
    try:
        record = build_service_record(body)
    except ValueError as e:
        return error_response(str(e), 400)

    # Check for duplicates (case-insensitive)
    try:
        existing_services = get_services_from_db(uid)
        new_name_lower = record["service_name"].lower()
        if any(s.get("service_name", "").lower() == new_name_lower for s in existing_services):
            return error_response("Service already exists in database", 409)
    except Exception as e:
        return error_response(f"Database read failed during validation: {e}", 500)

    # Persist to Firebase Realtime Database
    try:
        stored = add_service_to_db(uid, record)
    except Exception as e:
        return error_response(f"Database write failed: {e}", 500)

    return success_response(
        data=stored,
        message=f"Service '{record['service_name']}' added successfully.",
        status=201
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# GET /get_services
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@app.route("/get_services", methods=["GET"])
def get_services():
    """
    Retrieve all cloud services stored for the authenticated user.

    Headers:
        Authorization: Bearer <idToken>

    Optional query parameters:
        sort_by  : field name to sort by          (default: timestamp)
        order    : 'asc' or 'desc'                (default: desc)
        limit    : max number of records to return (default: all)

    Success (200):
    {
        "status":  "success",
        "message": "Success",
        "data": {
            "count": 3,
            "services": [
                {
                    "id":           "-NxABC123...",
                    "service_name": "AWS EC2 t3.medium",
                    "response_time": 120.5,
                    "throughput":    850.0,
                    "security":      88.0,
                    "cost":          250.0,
                    "timestamp":    "2026-03-11T16:28:00Z"
                },
                ...
            ]
        }
    }
    """
    uid, err = _require_auth()
    if err:
        return err

    # Fetch all services from Firebase
    try:
        services = get_services_from_db(uid)
    except Exception as e:
        return error_response(f"Database read failed: {e}", 500)

    # â”€â”€ Optional filtering / sorting via query params    # ── Optional filtering / sorting via query params ──────────────────────
    sort_by = request.args.get("sort_by", "timestamp")
    order   = request.args.get("order",   "desc").lower()
    limit   = request.args.get("limit", 10)
    page    = request.args.get("page", 1)
    search  = request.args.get("search", "").strip().lower()

    if search:
        services = [s for s in services if search in s.get("service_name", "").lower()]

    valid_sort_fields = ["service_name", "response_time", "throughput",
                         "security", "cost", "timestamp"]
    if sort_by not in valid_sort_fields:
        sort_by = "timestamp"

    reverse = (order == "desc")
    services.sort(
        key=lambda s: s.get(sort_by) or 0 if sort_by != "service_name" else s.get(sort_by, ""),
        reverse=reverse
    )

    total_count = len(services)
    avg_response_time = round(sum(s.get("response_time", 0) for s in services) / total_count, 2) if total_count > 0 else 0
    avg_throughput = round(sum(s.get("throughput", 0) for s in services) / total_count, 2) if total_count > 0 else 0
    try:
        limit_num = int(limit)
        page_num = int(page)
        if page_num < 1:
            page_num = 1
            
        start_idx = (page_num - 1) * limit_num
        end_idx = start_idx + limit_num
        services = services[start_idx:end_idx]
        total_pages = (total_count + limit_num - 1) // limit_num if limit_num > 0 else 1
    except (ValueError, TypeError):
        limit_num = total_count
        page_num = 1
        total_pages = 1

    return success_response(
        data={
            "count": total_count,
            "avg_response_time": avg_response_time,
            "avg_throughput": avg_throughput,
            "page": page_num,
            "limit": limit_num,
            "total_pages": total_pages,
            "services": services
        }
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# DELETE /delete_service/<service_id>
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@app.route("/delete_service/<service_id>", methods=["DELETE"])
def delete_service(service_id: str):
    """
    Delete a specific service record by its Firebase push key.

    Headers:
        Authorization: Bearer <idToken>

    Success (200): { "status": "success", "message": "Service deleted." }
    Not found (404): { "status": "error", "message": "Service not found." }
    """
    uid, err = _require_auth()
    if err:
        return err

    try:
        found = delete_service_from_db(uid, service_id)
    except Exception as e:
        return error_response(f"Database delete failed: {e}", 500)

    if not found:
        return error_response(
            f"Service '{service_id}' not found. "
            "Use GET /get_services to see valid IDs.", 404
        )

    return success_response(message=f"Service '{service_id}' deleted.")


# ══════════════════════════════════════════════════════════════════════════════
# PUT /update_service/<service_id>
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/update_service/<service_id>", methods=["PUT"])
def update_service(service_id: str):
    """
    Update specific QoS fields for an existing service.
    Accepts: { "response_time": X, "throughput": Y, "security": Z, "cost": W }
    """
    from database import update_service_in_db, SERVICE_NUMERIC_FIELDS
    uid, err = _require_auth()
    if err:
        return err

    body = request.get_json(silent=True)
    if not body:
        return error_response("Request body must be JSON.", 400)

    updates = {}
    for field in SERVICE_NUMERIC_FIELDS:
        if field in body:
            raw = body[field]
            try:
                val = float(raw)
                updates[field] = val
            except (TypeError, ValueError):
                return error_response(f"Field '{field}' must be a number.", 400)

    if "security" in updates and not (0 <= updates["security"] <= 100):
        return error_response("'security' must be between 0 and 100.", 400)
    for field in ["response_time", "throughput", "cost"]:
        if field in updates and updates[field] < 0:
            return error_response(f"'{field}' cannot be negative.", 400)

    if not updates:
        return error_response("No valid fields to update.", 400)

    try:
        updated_record = update_service_in_db(uid, service_id, updates)
        return success_response(data=updated_record, message="Service updated successfully.")
    except Exception as e:
        return error_response(f"Update failed: {str(e)}", 500)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# DELETE /delete_all_services
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@app.route("/delete_all_services", methods=["DELETE"])
def delete_all_services():
    """
    Delete ALL service records for the authenticated user.

    Headers:
        Authorization: Bearer <idToken>
    """
    uid, err = _require_auth()
    if err:
        return err

    try:
        delete_all_services_from_db(uid)
    except Exception as e:
        return error_response(f"Database delete failed: {e}", 500)

    return success_response(message="All services deleted successfully.")

# ══════════════════════════════════════════════════════════════════════════════
# POST /rank_services
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/rank_services", methods=["POST", "OPTIONS"])
def rank_services_root():
    """
    Retrieve services from Realtime DB, run Entropy Weight + TOPSIS, return results.
    Alias for POST /services/rank.
    """
    if request.method == "OPTIONS":
        return jsonify({}), 200

    from algorithm import run_ranking
    from utils import validate_manual_entries

    uid, err = _require_auth()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    inline = body.get("services")

    if inline:
        try:
            services = validate_manual_entries(inline)
        except ValueError as e:
            return error_response(str(e), 400)
    else:
        services = get_services_from_db(uid)

    if len(services) < 2:
        return error_response("At least 2 cloud services are needed to rank.", 400)

    try:
        result_df, weights, criteria = run_ranking(services)
    except ValueError as e:
        return error_response(str(e), 400)

    ranked = result_df.to_dict(orient="records")
    weight_dict = {c: round(float(w), 6) for c, w in zip(criteria, weights)}

    return success_response(
        data={
            "ranked":  ranked,
            "weights": weight_dict,
            "criteria": criteria,
            "best":    result_df.iloc[0]["service_name"],
        },
        message="Ranking computed successfully."
    )


# ── Health check ──────────────────────────────────────────────────────────
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "app": "Dynamic Cloud Service Composition System"})

    # ── Global error handlers ─────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "message": "Endpoint not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"status": "error", "message": "Method not allowed."}), 405

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"status": "error", "message": "Internal server error."}), 500

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(
        host="0.0.0.0",
        port=int(os.environ.get("FLASK_PORT", 5000)),
        debug=True
    )
