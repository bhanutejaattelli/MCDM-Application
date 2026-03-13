import pandas as pd
import numpy as np
from io import BytesIO
from algorithm import QOS_CRITERIA
"""
services.py â€” Cloud service CRUD routes backed by Firebase Realtime Database.
All data is scoped per user (uid) under /services/{uid}/ in the database.

DB helpers are provided by database.py (single source of truth for all
Realtime DB interactions in this project).
"""
from flask import Blueprint, request, jsonify
from firebase_config import verify_id_token
from algorithm import run_ranking
from database import (
    add_service_to_db,
    get_services_from_db,
    delete_service_from_db,
    delete_all_services_from_db,
    build_service_record,
    utc_now,
)

services_bp = Blueprint("services", __name__, url_prefix="/services")


# â”€â”€ Auth middleware helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _get_uid() -> str | None:
    """Extract and verify Firebase ID token from Authorization header."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        decoded = verify_id_token(header.split("Bearer ")[1].strip())
        return decoded["uid"]
    except Exception:
        return None


def require_auth():
    uid = _get_uid()
    if not uid:
        return None, error_response("Unauthorized. Please login.", 401)
    return uid, None


# â”€â”€ POST /services/upload â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@services_bp.route("/upload", methods=["POST"])
def upload_excel():
    """
    Multipart form: 'file' field with an .xlsx file.
    Parses Excel, stores each service in Realtime DB under /services/{uid}/
    Returns the list of stored services with their generated keys.
    """
    uid, err = require_auth()
    if err:
        return err

    if "file" not in request.files:
        return error_response("No file provided. Send an .xlsx file in 'file' field.", 400)

    file = request.files["file"]
    if not file.filename.endswith((".xlsx", ".xls")):
        return error_response("Only .xlsx / .xls files are accepted.", 400)
"""
services.py â€” Cloud service CRUD routes backed by Firebase Realtime Database.
All data is scoped per user (uid) under /services/{uid}/ in the database.

DB helpers are provided by database.py (single source of truth for all
Realtime DB interactions in this project).
"""
from flask import Blueprint, request, jsonify
from firebase_config import verify_id_token
from algorithm import run_ranking
from database import (
    add_service_to_db,
    get_services_from_db,
    delete_service_from_db,
    delete_all_services_from_db,
    build_service_record,
    utc_now,
)

services_bp = Blueprint("services", __name__, url_prefix="/services")


# â”€â”€ Auth middleware helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _get_uid() -> str | None:
    """Extract and verify Firebase ID token from Authorization header."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        decoded = verify_id_token(header.split("Bearer ")[1].strip())
        return decoded["uid"]
    except Exception:
        return None


def require_auth():
    uid = _get_uid()
    if not uid:
        return None, error_response("Unauthorized. Please login.", 401)
    return uid, None


# â”€â”€ POST /services/upload â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@services_bp.route("/upload", methods=["POST"])
def upload_excel():
    """
    Multipart form: 'file' field with an .xlsx file.
    Parses Excel, stores each service in Realtime DB under /services/{uid}/
    Returns the list of stored services with their generated keys.
    """
    uid, err = require_auth()
    if err:
        return err

    if "file" not in request.files:
        return error_response("No file provided. Send an .xlsx file in 'file' field.", 400)

    file = request.files["file"]
    if not file.filename.endswith((".xlsx", ".xls")):
        return error_response("Only .xlsx / .xls files are accepted.", 400)

    try:
        services = parse_excel(file.read())
    except ValueError as e:
        return error_response(str(e), 400)

    stored, skipped = _store_services(uid, services)
    
    msg = f"{len(stored)} services uploaded and stored successfully."
    if skipped > 0:
        msg += f" {skipped} duplicate services skipped during upload."
        
    return success_response(
        data={"count": len(stored), "skipped": skipped, "services": stored},
        message=msg.strip(),
        status=201
    )


# â”€â”€ POST /services/manual â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@services_bp.route("/manual", methods=["POST"])
def add_manual():
    """
    Body: { "services": [{ServiceName, Availability, ResponseTime, ...}, ...] }
    Validates and stores each service in Realtime DB.
    """
    uid, err = require_auth()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    raw_services = body.get("services", [])

    try:
        services = validate_manual_entries(raw_services)
    except ValueError as e:
        return error_response(str(e), 400)

    stored, skipped = _store_services(uid, services)
    
    msg = f"{len(stored)} services added successfully."
    if skipped > 0:
        msg += f" {skipped} duplicate services skipped."
        
    return success_response(
        data={"count": len(stored), "skipped": skipped, "services": stored},
        message=msg.strip(),
        status=201
    )


# â”€â”€ GET /services/list â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@services_bp.route("/list", methods=["GET"])
def list_services():
    """Return all services stored for the authenticated user."""
    uid, err = require_auth()
    if err:
        return err

    items = get_services_from_db(uid)
    return success_response(data={"count": len(items), "services": items})


# â”€â”€ DELETE /services/<service_id> â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@services_bp.route("/<service_id>", methods=["DELETE"])
def delete_service(service_id: str):
    """Delete a single service record."""
    uid, err = require_auth()
    if err:
        return err

    found = delete_service_from_db(uid, service_id)
    if not found:
        return error_response("Service not found.", 404)
    return success_response(message=f"Service '{service_id}' deleted.")


# â”€â”€ DELETE /services/all â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@services_bp.route("/all", methods=["DELETE"])
def delete_all_services():
    """Delete ALL services for the authenticated user."""
    uid, err = require_auth()
    if err:
        return err

    delete_all_services_from_db(uid)
    return success_response(message="All services deleted.")


# â”€â”€ POST /services/rank â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@services_bp.route("/rank", methods=["POST"])
def rank_services():
    """
    Retrieve services from Realtime DB, run Entropy Weight + TOPSIS, return results.
    Optionally accepts inline services via body: { "services": [...] }
    """
    uid, err = require_auth()
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


# â”€â”€ Internal: store services in Realtime DB â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _store_services(uid: str, services: list[dict]) -> tuple[list[dict], int]:
    """Push each service to /services/{uid}/ via database.py skipping duplicates, and return stored records and skip count."""
    existing_services = get_services_from_db(uid)
    existing_names = {s.get("service_name", "").lower() for s in existing_services}

    stored = []
    skipped_count = 0
    for service in services:
        name_lower = service.get("service_name", "").lower()
        if name_lower in existing_names:
            skipped_count += 1
            continue  # Skip duplicate

        # Ensure timestamp is set before storing
        if "timestamp" not in service:
            service["timestamp"] = utc_now()
            
        stored_record = add_service_to_db(uid, service)
        stored.append(stored_record)
        existing_names.add(name_lower)

    return stored, skipped_count


# --- UTILS MIGRATED --- 
"""
utils.py — Helper functions: Excel parsing, data validation, response builders.
"""
import pandas as pd
import numpy as np
from io import BytesIO


# ── Excel / Data parsing ──────────────────────────────────────────────────────
def parse_excel(file_bytes: bytes) -> list[dict]:
    """
    Parse an uploaded Excel file into a list of service dicts.
    Expected columns: "Service", "Response Time", "Throughput", "Security", "Cost"
    Returns a list of dicts with mapped database schema keys.
    """
    df = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    # Map user-friendly Excel columns to DB schema fields
    col_map = {
        "Service": "service_name",
        "Response Time": "response_time",
        "Throughput": "throughput",
        "Security": "security",
        "Cost": "cost"
    }

    missing = [c for c in col_map.keys() if c not in df.columns]
    if missing:
        raise ValueError(
            f"Excel file is missing required columns: {', '.join(missing)}. "
            f"Expected exactly: {', '.join(col_map.keys())}"
        )

    # Drop rows with missing service names
    df = df.dropna(subset=["Service"])
    
    # Coerce numerics
    num_cols = ["Response Time", "Throughput", "Security", "Cost"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    # Clean strings
    df["Service"] = df["Service"].astype(str).str.strip()

    # Rename & export
    df = df.rename(columns=col_map)
    return df[list(col_map.values())].to_dict(orient="records")


def validate_manual_entries(data: list[dict]) -> list[dict]:
    """
    Validate manually entered service records.
    Each dict must have 'service_name' and the specific numeric fields.
    """
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Expected a non-empty list of service records.")

    validated = []
    for i, item in enumerate(data):
        if "service_name" not in item or not str(item["service_name"]).strip():
            raise ValueError(f"Record {i+1}: 'service_name' is required.")
        
        clean = {"service_name": str(item["service_name"]).strip()}
        for crit in QOS_CRITERIA:
            if crit in item:
                try:
                    clean[crit] = float(item[crit])
                except (ValueError, TypeError):
                    clean[crit] = 0.0
        validated.append(clean)
    return validated


# ── Response builders ─────────────────────────────────────────────────────────
from flask import jsonify as _jsonify

def success_response(data=None, message="Success", status=200):
    """Return a Flask (Response, status_code) tuple with a success JSON body.
    Usage in routes:  return success_response(data={...}, message="OK", status=201)
    """
    body = {"status": "success", "message": message}
    if data is not None:
        body["data"] = data
    return _jsonify(body), status


def error_response(message="Error", status=400):
    """Return a Flask (Response, status_code) tuple with an error JSON body.
    Usage in routes:  return error_response("Not found.", 404)
    """
    return _jsonify({"status": "error", "message": message}), status



# ── DataFrame helper ──────────────────────────────────────────────────────────
def services_to_dataframe(services: list[dict]) -> pd.DataFrame:
    """Convert a list of service dicts to a pandas DataFrame with numeric QoS columns."""
    df = pd.DataFrame(services)
    for crit in QOS_CRITERIA:
        if crit in df.columns:
            df[crit] = pd.to_numeric(df[crit], errors="coerce").fillna(0)
    return df
