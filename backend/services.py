"""
services.py — Cloud service CRUD routes backed by Firebase Realtime Database.
"""
from flask import Blueprint, request, jsonify
import pandas as pd
from io import BytesIO
from database import (
    add_service_to_db,
    get_services_from_db,
    delete_service_from_db,
    delete_all_services_from_db,
    update_service_in_db,
    build_service_record,
    verify_id_token,
)
from algorithm import run_ranking, QOS_CRITERIA



services_bp = Blueprint("services", __name__)


# ── Auth middleware helper ────────────────────────────────────────────────────────
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


# ── Routes ────────────────────────────────────────────────────────────────────────

@services_bp.route("", methods=["GET"])
def list_services():
    """GET /services — List all services with filtering, sorting, and pagination."""
    uid, err = require_auth()
    if err: return err
    try:
        services = get_services_from_db(uid)
        
        # Search
        search = request.args.get("search", "").strip().lower()
        if search:
            services = [s for s in services if search in s.get("service_name", "").lower()]
        
        # Sort
        sort_by = request.args.get("sort_by", "timestamp")
        order = request.args.get("order", "desc").lower()
        reverse = (order == "desc")
        services.sort(key=lambda s: s.get(sort_by) or (0 if sort_by != "service_name" else ""), reverse=reverse)

        # Pagination
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


@services_bp.route("/manual", methods=["POST"])
def add_manual():
    """POST /services/manual — Add a single service manually."""
    uid, err = require_auth()
    if err: return err

    body = request.get_json(silent=True) or {}
    try:
        record = build_service_record(body)
        existing_services = get_services_from_db(uid)
        if any(s.get("service_name", "").lower() == record["service_name"].lower() for s in existing_services):
            return error_response("Service already exists in database", 409)
        stored = add_service_to_db(uid, record)
        return success_response(data=stored, message=f"Service '{record['service_name']}' added.", status=201)
    except Exception as e:
        return error_response(str(e), 500)


@services_bp.route("/upload", methods=["POST"])
def upload_excel():
    """POST /services/upload — Bulk upload services from Excel."""
    uid, err = require_auth()
    if err: return err

    if "file" not in request.files:
        return error_response("No file provided. Send an .xlsx file in 'file' field.", 400)

    file = request.files["file"]
    if not file.filename.endswith((".xlsx", ".xls")):
        return error_response("Only .xlsx / .xls files are accepted.", 400)

    try:
        raw_services = parse_excel(file.read())
        stored, skipped = _store_services(uid, raw_services)
        
        msg = f"{len(stored)} services uploaded successfully."
        if skipped > 0:
            msg += f" {skipped} duplicate(s) skipped."
            
        return success_response(
            data={"count": len(stored), "skipped": skipped, "services": stored},
            message=msg.strip(),
            status=201
        )
    except Exception as e:
        return error_response(str(e), 400)


@services_bp.route("/<service_id>", methods=["PUT"])
def update_service_route(service_id: str):
    """PUT /services/<id> — Update a service.")]"""
    uid, err = require_auth()
    if err: return err
    
    body = request.get_json(silent=True) or {}
    updates = {f: float(body[f]) for f in QOS_CRITERIA if f in body}
    
    if not updates: 
        return error_response("No valid fields to update.", 400)
    try:
        updated = update_service_in_db(uid, service_id, updates)
        return success_response(data=updated, message="Service updated.")
    except Exception as e:
        return error_response(str(e), 500)


@services_bp.route("/<service_id>", methods=["DELETE"])
def delete_service_route(service_id: str):
    """DELETE /services/<id> — Delete a specific service."""
    uid, err = require_auth()
    if err: return err
    if delete_service_from_db(uid, service_id):
        return success_response(message="Service deleted.")
    return error_response("Service not found.", 404)


@services_bp.route("", methods=["DELETE"])
def delete_all_services_route():
    """DELETE /services — Delete all services for the user."""
    uid, err = require_auth()
    if err: return err
    delete_all_services_from_db(uid)
    return success_response(message="All services deleted.")


@services_bp.route("/rank", methods=["POST", "OPTIONS"])
def rank_services_bp():
    """POST /services/rank — Calculate MCDM ranking."""
    if request.method == "OPTIONS": return jsonify({}), 200
    uid, err = require_auth()
    if err: return err

    try:
        services = get_services_from_db(uid)
        if len(services) < 2:
            return error_response("At least 2 services are needed to rank.", 400)
        
        result_df, weights, criteria = run_ranking(services)
        return success_response(data={
            "ranked":  result_df.to_dict(orient="records"),
            "weights": {c: round(float(w), 6) for c, w in zip(criteria, weights)},
            "criteria": list(criteria),
            "best":    result_df.iloc[0]["service_name"],
        }, message="Ranking computed.")
    except Exception as e:
        return error_response(str(e), 500)


@services_bp.route("/import-global", methods=["POST"])
def import_global_services():
    """POST /services/import-global — Import services from global DB to user's personal DB."""
    uid, err = require_auth()
    if err: return err

    body = request.get_json(silent=True) or {}
    provider_ids = body.get("provider_ids", [])  # Optional: specific IDs to import

    try:
        from database import get_global_providers

        global_providers = get_global_providers()

        if not global_providers:
            return error_response("No global providers available to import.", 404)

        # Filter by specific IDs if provided
        if provider_ids:
            global_providers = [p for p in global_providers if p.get("id") in provider_ids]
            if not global_providers:
                return error_response("None of the specified provider IDs were found.", 404)

        # Get existing services to avoid duplicates
        existing = get_services_from_db(uid)
        existing_names = {s.get("service_name", "").lower() for s in existing}

        imported = []
        skipped = 0
        for provider in global_providers:
            service_name = provider.get("name", "Unknown")

            # Skip if already exists in user's personal DB
            if service_name.lower() in existing_names:
                skipped += 1
                continue

            # Build a service record from the global provider data
            record = build_service_record({
                "service_name":  service_name,
                "response_time": provider.get("response_time", 0),
                "throughput":    provider.get("throughput", 0),
                "security":      provider.get("security", 0),
                "cost":          provider.get("cost", 0),
            })

            stored = add_service_to_db(uid, record)
            imported.append(stored)
            existing_names.add(service_name.lower())

        msg = f"{len(imported)} services imported successfully."
        if skipped > 0:
            msg += f" {skipped} duplicate(s) skipped."

        return success_response(
            data={"imported_count": len(imported), "skipped": skipped, "services": imported},
            message=msg,
            status=201
        )
    except Exception as e:
        return error_response(str(e), 500)


# ── Internal Helpers ──────────────────────────────────────────────────────────────


def _store_services(uid: str, services: list[dict]) -> tuple[list[dict], int]:
    existing_services = get_services_from_db(uid)
    existing_names = {s.get("service_name", "").lower() for s in existing_services}
    stored = []
    skipped = 0
    for s in services:
        name = s.get("service_name", "").lower()
        if name in existing_names:
            skipped += 1
            continue
        record = build_service_record(s)
        res = add_service_to_db(uid, record)
        stored.append(res)
        existing_names.add(name)
    return stored, skipped


def parse_excel(file_bytes: bytes) -> list[dict]:
    df = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {
        "Service": "service_name", "Response Time": "response_time",
        "Throughput": "throughput", "Security": "security", "Cost": "cost"
    }
    missing = [c for c in col_map.keys() if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    df = df.dropna(subset=["Service"])
    for col in ["Response Time", "Throughput", "Security", "Cost"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    df = df.rename(columns=col_map)
    return df[list(col_map.values())].to_dict(orient="records")


def success_response(data=None, message="Success", status=200):
    body = {"status": "success", "message": message}
    if data is not None: body["data"] = data
    return jsonify(body), status


def error_response(message="Error", status=400):
    return jsonify({"status": "error", "message": message}), status
