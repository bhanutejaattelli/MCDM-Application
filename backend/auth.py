"""
auth.py â€” Firebase Authentication Flask Blueprint.

Endpoints:
  POST  /auth/register  â†’ Create account + store user profile in Realtime DB
  POST  /auth/login     â†’ Sign in, return ID token + user profile
  POST  /auth/logout    â†’ Revoke refresh tokens (server-side session invalidation)
  POST  /auth/verify    â†’ Verify ID token, return decoded claims
  POST  /auth/refresh   â†’ Exchange refresh token for new ID token
  GET   /auth/profile   â†’ Fetch authenticated user's profile from Realtime DB
  PUT   /auth/profile   â†’ Update user's display name in Auth + Realtime DB

All protected routes require:  Authorization: Bearer <idToken>
"""

import datetime
from flask import Blueprint, request, jsonify
from firebase_admin import auth as admin_auth
from database import get_pyrebase_auth, get_db_ref, verify_id_token, refresh_session_token
from services import success_response, error_response

auth_bp = Blueprint("auth", __name__)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Internal helpers
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _get_uid() -> tuple[str | None, object]:
    """Extract and verify Bearer token â†’ return (uid, None) or (None, error_response)."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, error_response("Missing or malformed Authorization header.", 401)
    try:
        decoded = verify_id_token(header.split("Bearer ")[1].strip())
        return decoded["uid"], None
    except Exception as e:
        return None, error_response(f"Invalid or expired token: {e}", 401)


def _save_user_to_db(uid: str, email: str, display_name: str) -> None:
    """Persist a user record under /users/{uid} in Firebase Realtime Database."""
    get_db_ref(f"/users/{uid}").set({
        "uid":         uid,
        "email":       email,
        "displayName": display_name,
        "createdAt":   datetime.datetime.utcnow().isoformat() + "Z",
        "lastLoginAt": datetime.datetime.utcnow().isoformat() + "Z",
    })


def _update_last_login(uid: str) -> None:
    """Update only the lastLoginAt field so we don't overwrite other profile data."""
    try:
        get_db_ref(f"/users/{uid}").update({
            "lastLoginAt": datetime.datetime.utcnow().isoformat() + "Z"
        })
    except Exception:
        pass   # non-critical


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# POST /auth/register
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Body JSON:
    {
        "email":       "user@example.com",
        "password":    "secret123",
        "displayName": "Alice"         (optional)
    }

    Creates a Firebase Auth user, stores profile in Realtime DB.
    Returns 201 with idToken on success.
    """
    body         = request.get_json(silent=True) or {}
    email        = body.get("email", "").strip().lower()
    password     = body.get("password", "")
    display_name = body.get("displayName", "").strip()

    # â”€â”€ Validation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not email:
        return error_response("Email is required.", 400)
    if "@" not in email:
        return error_response("Invalid email address.", 400)
    if not password:
        return error_response("Password is required.", 400)
    if len(password) < 6:
        return error_response("Password must be at least 6 characters.", 400)

    try:
        # Create user via Pyrebase (returns idToken immediately)
        pb_user  = get_pyrebase_auth().create_user_with_email_and_password(email, password)
        uid      = pb_user["localId"]
        id_token = pb_user["idToken"]

        # Set displayName in Firebase Auth via Admin SDK
        name_to_store = display_name or email.split("@")[0]
        admin_auth.update_user(uid, display_name=name_to_store)

        # â”€â”€ Persist profile to Realtime Database â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _save_user_to_db(uid, email, name_to_store)

        return success_response(
            data={
                "uid":         uid,
                "email":       email,
                "displayName": name_to_store,
                "idToken":     id_token,
            },
            message="Account created successfully.",
            status=201
        )

    except Exception as e:
        msg = str(e)
        if "EMAIL_EXISTS" in msg:
            return error_response("An account with this email already exists.", 409)
        if "WEAK_PASSWORD" in msg:
            return error_response("Password is too weak. Use at least 6 characters.", 400)
        if "INVALID_EMAIL" in msg:
            return error_response("Invalid email format.", 400)
        return error_response(f"Registration failed: {msg}", 500)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# POST /auth/login
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Body JSON:
    {
        "email":    "user@example.com",
        "password": "secret123"
    }

    Returns idToken, refreshToken, user profile on success.
    """
    body     = request.get_json(silent=True) or {}
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        return error_response("Email and password are required.", 400)

    try:
        pb_user = get_pyrebase_auth().sign_in_with_email_and_password(email, password)
        uid     = pb_user["localId"]

        # Fetch display name from Admin SDK
        try:
            admin_user   = admin_auth.get_user(uid)
            display_name = admin_user.display_name or email.split("@")[0]
        except Exception:
            display_name = email.split("@")[0]

        # Update last login timestamp in Realtime DB (non-blocking)
        _update_last_login(uid)

        return success_response(
            data={
                "uid":          uid,
                "email":        pb_user["email"],
                "displayName":  display_name,
                "idToken":      pb_user["idToken"],
                "refreshToken": pb_user["refreshToken"],
                "expiresIn":    pb_user["expiresIn"],
            },
            message="Login successful."
        )

    except Exception as e:
        msg = str(e)
        if any(x in msg for x in ("INVALID_PASSWORD", "EMAIL_NOT_FOUND",
                                   "INVALID_LOGIN_CREDENTIALS", "USER_NOT_FOUND")):
            return error_response("Invalid email or password.", 401)
        if "USER_DISABLED" in msg:
            return error_response("This account has been disabled.", 403)
        if "TOO_MANY_ATTEMPTS" in msg:
            return error_response("Too many failed attempts. Try again later.", 429)
        return error_response(f"Login failed: {msg}", 500)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# POST /auth/logout
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Revokes ALL refresh tokens for the authenticated user (server-side logout).
    Header: Authorization: Bearer <idToken>

    The frontend should also clear its local session state.
    """
    uid, err = _get_uid()
    if err:
        return err

    try:
        admin_auth.revoke_refresh_tokens(uid)
        return success_response(message="Logged out successfully. All sessions invalidated.")
    except Exception as e:
        return error_response(f"Logout failed: {e}", 500)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# POST /auth/verify
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@auth_bp.route("/verify", methods=["POST"])
def verify_token():
    """
    Body JSON: { "idToken": "<Firebase ID token>" }
    Returns decoded token claims (uid, email) if valid.
    """
    body     = request.get_json(silent=True) or {}
    id_token = body.get("idToken", "").strip()

    if not id_token:
        return error_response("idToken is required.", 400)

    try:
        decoded = verify_id_token(id_token)
        return success_response(
            data={
                "uid":   decoded["uid"],
                "email": decoded.get("email", ""),
                "valid": True,
            },
            message="Token is valid."
        )
    except Exception as e:
        return error_response(f"Token invalid or expired: {e}", 401)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# POST /auth/refresh
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """
    Body JSON: { "refreshToken": "<Firebase refresh token>" }
    Returns a new idToken (Firebase ID tokens expire after 1 hour).
    """
    body          = request.get_json(silent=True) or {}
    refresh_tok   = body.get("refreshToken", "").strip()

    if not refresh_tok:
        return error_response("refreshToken is required.", 400)

    try:
        result = refresh_session_token(refresh_tok)
        return success_response(
            data=result,
            message="Token refreshed successfully."
        )
    except Exception as e:
        return error_response(f"Token refresh failed: {e}", 401)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# GET /auth/profile
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@auth_bp.route("/profile", methods=["GET"])
def get_profile():
    """
    Returns full user profile stored in Realtime Database + Auth metadata.
    Header: Authorization: Bearer <idToken>
    """
    uid, err = _get_uid()
    if err:
        return err

    try:
        db_profile = get_db_ref(f"/users/{uid}").get() or {}

        # Enrich with Firebase Auth metadata
        admin_user = admin_auth.get_user(uid)
        return success_response(data={
            "uid":           uid,
            "email":         admin_user.email,
            "displayName":   admin_user.display_name,
            "emailVerified": admin_user.email_verified,
            "createdAt":     db_profile.get("createdAt"),
            "lastLoginAt":   db_profile.get("lastLoginAt"),
        })
    except Exception as e:
        return error_response(f"Failed to fetch profile: {e}", 500)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PUT /auth/profile
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@auth_bp.route("/profile", methods=["PUT"])
def update_profile():
    """
    Update displayName in Firebase Auth + Realtime DB.
    Header: Authorization: Bearer <idToken>
    Body JSON: { "displayName": "New Name" }
    """
    uid, err = _get_uid()
    if err:
        return err

    body         = request.get_json(silent=True) or {}
    display_name = body.get("displayName", "").strip()

    if not display_name:
        return error_response("displayName is required.", 400)

    try:
        admin_auth.update_user(uid, display_name=display_name)
        get_db_ref(f"/users/{uid}").update({"displayName": display_name})
        return success_response(
            data={"uid": uid, "displayName": display_name},
            message="Profile updated successfully."
        )
    except Exception as e:
        return error_response(f"Update failed: {e}", 500)

