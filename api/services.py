"""
services.py — Cloud service CRUD routes backed by Firebase Realtime Database.
"""
from flask import Blueprint, request, jsonify
import pandas as pd
import numpy as np
from io import BytesIO
from database import (
    add_service_to_db,
    get_services_from_db,
    delete_service_from_db,
    delete_all_services_from_db,
    build_service_record,
    utc_now,
    verify_id_token,
)
from algorithm import run_ranking, QOS_CRITERIA

services_bp = Blueprint("services", __name__, url_prefix="/services")


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

@services_bp.route("/upload", methods=["POST"])
def upload_excel():
    uid, err = require_auth()
    if err: return err

    if "file" not in request.files:
        return error_response("No file provided. Send an .xlsx file in 'file' field.", 400)

    file = request.files["file"]
    if not file.filename.endswith((".xlsx", ".xls")):
        return error_response("Only .xlsx / .xls files are accepted.", 400)

    try:
        services = parse_excel(file.read())
    except Exception as e:
        return error_response(str(e), 400)

    stored, skipped = _store_services(uid, services)
    
    msg = f"{len(stored)} services uploaded successfully."
    if skipped > 0:
        msg += f" {skipped} duplicate(s) skipped."
        
    return success_response(
        data={"count": len(stored), "skipped": skipped, "services": stored},
        message=msg.strip(),
        status=201
    )


@services_bp.route("/manual", methods=["POST"])
def add_manual():
    uid, err = require_auth()
    if err: return err

    body = request.get_json(silent=True) or {}
    raw_services = body.get("services", [])

    try:
        services = validate_manual_entries(raw_services)
    except Exception as e:
        return error_response(str(e), 400)

    stored, skipped = _store_services(uid, services)
    
    msg = f"{len(stored)} services added successfully."
    if skipped > 0:
        msg += f" {skipped} duplicate(s) skipped."
        
    return success_response(
        data={"count": len(stored), "skipped": skipped, "services": stored},
        message=msg.strip(),
        status=201
    )


@services_bp.route("/list", methods=["GET"])
def list_services():
    uid, err = require_auth()
    if err: return err
    items = get_services_from_db(uid)
    return success_response(data={"count": len(items), "services": items})


@services_bp.route("/<service_id>", methods=["DELETE"])
def delete_service_route(service_id: str):
    uid, err = require_auth()
    if err: return err
    if delete_service_from_db(uid, service_id):
        return success_response(message="Service deleted.")
    return error_response("Service not found.", 404)


@services_bp.route("/all", methods=["DELETE"])
def delete_all_services_route():
    uid, err = require_auth()
    if err: return err
    delete_all_services_from_db(uid)
    return success_response(message="All services deleted.")


@services_bp.route("/rank", methods=["POST"])
def rank_services_bp():
    uid, err = require_auth()
    if err: return err

    body = request.get_json(silent=True) or {}
    inline = body.get("services")

    if inline:
        try:
            services = validate_manual_entries(inline)
        except Exception as e:
            return error_response(str(e), 400)
    else:
        services = get_services_from_db(uid)

    if len(services) < 2:
        return error_response("At least 2 services are needed to rank.", 400)

    try:
        result_df, weights, criteria = run_ranking(services)
        return success_response(data={
            "ranked":  result_df.to_dict(orient="records"),
            "weights": {c: round(float(w), 6) for c, w in zip(criteria, weights)},
            "criteria": list(criteria),
            "best":    result_df.iloc[0]["service_name"],
        }, message="Ranking computed.")
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


def validate_manual_entries(data: list[dict]) -> list[dict]:
    if not isinstance(data, list) or not data:
        raise ValueError("Invalid services list.")
    validated = []
    for item in data:
        name = str(item.get("service_name", "")).strip()
        if not name: continue
        clean = {"service_name": name}
        for crit in QOS_CRITERIA:
            try: clean[crit] = float(item.get(crit, 0))
            except: clean[crit] = 0.0
        validated.append(clean)
    return validated


def success_response(data=None, message="Success", status=200):
    body = {"status": "success", "message": message}
    if data is not None: body["data"] = data
    return jsonify(body), status


def error_response(message="Error", status=400):
    return jsonify({"status": "error", "message": message}), status


def services_to_dataframe(services: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(services)
    for crit in QOS_CRITERIA:
        if crit in df.columns:
            df[crit] = pd.to_numeric(df[crit], errors="coerce").fillna(0)
    return df
