"""
admin.py — Admin Blueprint for RBAC + Global Provider Management.

Endpoints:
  GET    /api/global-providers              → List all global providers (any auth user)
  POST   /api/global-providers              → Add a global provider (admin only)
  PUT    /api/global-providers/<id>         → Update a global provider (admin only)
  DELETE /api/global-providers/<id>         → Delete a global provider (admin only)
  POST   /api/global-providers/refresh     → Trigger pricing data refresh (admin only)
  POST   /api/admin/make-admin              → Promote a user to admin (admin only)
  POST   /api/admin/remove-admin            → Demote admin to user (admin only)
  GET    /api/admin/users                   → List all users (admin only)
  GET    /api/admin/update-logs             → Get recent update logs (admin only)
"""

import functools
from flask import Blueprint, request
from io import BytesIO
import pandas as pd
from database import (
    verify_id_token, get_user_role, set_user_role,
    get_all_users, get_global_providers,
    add_global_provider, update_global_provider,
    delete_global_provider, get_update_logs, utc_now,
    get_db_ref,
)
from services import success_response, error_response
from cloud_pricing import update_global_db

admin_bp = Blueprint("admin", __name__)


# ══════════════════════════════════════════════════════════════════════════════
# Auth helpers
# ══════════════════════════════════════════════════════════════════════════════

def _get_uid_from_request():
    """Extract and verify Bearer token → return (uid, None) or (None, error)."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, error_response("Missing or malformed Authorization header.", 401)
    try:
        decoded = verify_id_token(header.split("Bearer ")[1].strip())
        return decoded["uid"], None
    except Exception as e:
        return None, error_response(f"Invalid or expired token: {e}", 401)


def admin_required(f):
    """Decorator that ensures the caller is an authenticated admin."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        uid, err = _get_uid_from_request()
        if err:
            return err
        role = get_user_role(uid)
        if role != "admin":
            return error_response("Forbidden. Admin access required.", 403)
        request.admin_uid = uid
        return f(*args, **kwargs)
    return wrapper


def auth_required(f):
    """Decorator that ensures the caller is authenticated (any role)."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        uid, err = _get_uid_from_request()
        if err:
            return err
        request.user_uid = uid
        return f(*args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL PROVIDERS  — /api/global-providers
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/global-providers", methods=["GET"])
@auth_required
def list_global_providers():
    """GET /global-providers — List all global providers (any authenticated user)."""
    try:
        providers = get_global_providers()

        # Optional filtering
        provider_filter = request.args.get("provider", "").strip()
        type_filter = request.args.get("type", "").strip()
        search = request.args.get("search", "").strip().lower()

        if provider_filter:
            providers = [p for p in providers if p.get("provider", "").lower() == provider_filter.lower()]
        if type_filter:
            providers = [p for p in providers if p.get("type", "").lower() == type_filter.lower()]
        if search:
            providers = [p for p in providers if search in p.get("name", "").lower()]

        return success_response(data={
            "count": len(providers),
            "providers": providers,
        })
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/global-providers", methods=["POST"])
@admin_required
def create_global_provider():
    """POST /global-providers — Add a new global provider (admin only)."""
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    if not name:
        return error_response("'name' is required.", 400)

    try:
        record = {
            "name":          name,
            "provider":      body.get("provider", "Custom"),
            "type":          body.get("type", "Compute"),
            "cost":          float(body.get("cost", 0)),
            "response_time": float(body.get("response_time", 0)),
            "throughput":    float(body.get("throughput", 0)),
            "security":      float(body.get("security", 8)),
            "last_updated":  utc_now(),
        }
        result = add_global_provider(record)
        return success_response(data=result, message="Global provider added.", status=201)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/global-providers/upload", methods=["POST"])
@admin_required
def upload_global_providers():
    """POST /global-providers/upload — Bulk upload global providers via Excel."""
    if "file" not in request.files:
        return error_response("No file provided. Send an .xlsx file in 'file' field.", 400)

    file = request.files["file"]
    if not file.filename.endswith((".xlsx", ".xls")):
        return error_response("Only .xlsx / .xls files are accepted.", 400)

    try:
        raw_providers = parse_global_excel(file.read())
        added = 0
        for p in raw_providers:
            p["last_updated"] = utc_now()
            add_global_provider(p)
            added += 1
            
        return success_response(
            data={"count": added},
            message=f"{added} providers uploaded successfully.",
            status=201
        )
    except Exception as e:
        return error_response(str(e), 400)


def parse_global_excel(file_bytes: bytes) -> list[dict]:
    """Helper to parse a global providers Excel file into a list of dicts."""
    df = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {
        "Name": "name", "Provider": "provider", "Type": "type",
        "Cost": "cost", "Response Time": "response_time",
        "Throughput": "throughput", "Security": "security"
    }
    missing = [c for c in col_map.keys() if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    df = df.dropna(subset=["Name"])
    for col in ["Cost", "Response Time", "Throughput", "Security"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in ["Provider", "Type"]:
        df[col] = df[col].astype(str).fillna("Custom")
        
    df = df.rename(columns=col_map)
    return df[list(col_map.values())].to_dict(orient="records")


@admin_bp.route("/global-providers/<provider_id>", methods=["PUT"])
@admin_required
def update_global_provider_route(provider_id: str):
    """PUT /global-providers/<id> — Update a global provider (admin only)."""
    body = request.get_json(silent=True) or {}
    allowed_fields = {"name", "provider", "type", "cost", "response_time", "throughput", "security"}
    updates = {}
    for field in allowed_fields:
        if field in body:
            if field in ("cost", "response_time", "throughput", "security"):
                updates[field] = float(body[field])
            else:
                updates[field] = body[field]
    if not updates:
        return error_response("No valid fields to update.", 400)
    updates["last_updated"] = utc_now()

    try:
        result = update_global_provider(provider_id, updates)
        return success_response(data=result, message="Global provider updated.")
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/global-providers/<provider_id>", methods=["DELETE"])
@admin_required
def delete_global_provider_route(provider_id: str):
    """DELETE /global-providers/<id> — Delete a global provider (admin only)."""
    if delete_global_provider(provider_id):
        return success_response(message="Global provider deleted.")
    return error_response("Provider not found.", 404)



# ══════════════════════════════════════════════════════════════════════════════
# PRICING REFRESH — /api/global-providers/refresh
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/global-providers/refresh", methods=["POST"])
@admin_required
def refresh_global_providers():
    """POST /global-providers/refresh — Trigger cloud pricing data refresh (admin only)."""
    try:
        summary = update_global_db()
        if summary["status"] == "success":
            return success_response(data=summary, message=summary["message"])
        else:
            return error_response(summary["message"], 500)
    except Exception as e:
        return error_response(f"Refresh failed: {e}", 500)


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN MANAGEMENT — /api/admin
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/make-admin", methods=["POST"])
@admin_required
def make_admin():
    """POST /admin/make-admin — Promote a user to admin by email."""
    body = request.get_json(silent=True) or {}
    email = body.get("email", "").strip().lower()
    if not email:
        return error_response("'email' is required.", 400)

    try:
        # Find user by email
        users = get_all_users()
        target_user = None
        for u in users:
            if u.get("email", "").lower() == email:
                target_user = u
                break

        if not target_user:
            return error_response(f"No user found with email '{email}'.", 404)

        if target_user.get("role") == "admin":
            return error_response("User is already an admin.", 409)

        set_user_role(target_user["uid"], "admin")
        return success_response(
            data={"uid": target_user["uid"], "email": email, "role": "admin"},
            message=f"User '{email}' promoted to admin."
        )
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/admin/remove-admin", methods=["POST"])
@admin_required
def remove_admin():
    """POST /admin/remove-admin — Demote admin to regular user."""
    body = request.get_json(silent=True) or {}
    email = body.get("email", "").strip().lower()
    if not email:
        return error_response("'email' is required.", 400)

    try:
        users = get_all_users()
        target_user = None
        for u in users:
            if u.get("email", "").lower() == email:
                target_user = u
                break

        if not target_user:
            return error_response(f"No user found with email '{email}'.", 404)

        # Don't let admin demote themselves
        if target_user["uid"] == request.admin_uid:
            return error_response("You cannot remove your own admin role.", 400)

        if target_user.get("role") != "admin":
            return error_response("User is not an admin.", 409)

        set_user_role(target_user["uid"], "user")
        return success_response(
            data={"uid": target_user["uid"], "email": email, "role": "user"},
            message=f"Admin role removed from '{email}'."
        )
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/admin/users", methods=["GET"])
@admin_required
def list_users():
    """GET /admin/users — List all registered users (admin only)."""
    try:
        users = get_all_users()
        # Remove sensitive data
        safe_users = []
        for u in users:
            safe_users.append({
                "uid":         u.get("uid"),
                "email":       u.get("email"),
                "displayName": u.get("displayName"),
                "role":        u.get("role", "user"),
                "createdAt":   u.get("createdAt"),
                "lastLoginAt": u.get("lastLoginAt"),
            })
        return success_response(data={"count": len(safe_users), "users": safe_users})
    except Exception as e:
        return error_response(str(e), 500)


@admin_bp.route("/admin/update-logs", methods=["GET"])
@admin_required
def list_update_logs():
    """GET /admin/update-logs — Get recent update logs (admin only)."""
    try:
        limit = int(request.args.get("limit", 20))
        logs = get_update_logs(limit)
        return success_response(data={"count": len(logs), "logs": logs})
    except Exception as e:
        return error_response(str(e), 500)
