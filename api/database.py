"""
database.py — Firebase Realtime Database schema definitions and helper functions.

Database Structure
==================
/
├── users/
│   └── {uid}/
│       ├── uid           : string
│       ├── email         : string
│       ├── displayName   : string
│       ├── createdAt     : ISO-8601 string (UTC)
│       └── lastLoginAt   : ISO-8601 string (UTC)
│
└── services/
    └── {uid}/
        └── {push_id}/
            ├── service_name  : string          — Cloud provider / service label
            ├── response_time : float  (ms)     — Average latency (lower = better)
            ├── throughput    : float  (req/s)  — Requests per second (higher = better)
            ├── security      : float  (0-100)  — Security score (higher = better)
            ├── cost          : float  (USD/mo) — Monthly cost (lower = better)
            └── timestamp     : string (ISO-8601 UTC) — When the record was added
"""

import os
import datetime
import firebase_admin
from firebase_admin import credentials, auth as _admin_auth, db as _admin_db
import pyrebase
from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

firebase_cfg = {
    "apiKey":            os.getenv("FIREBASE_API_KEY"),
    "authDomain":        os.getenv("FIREBASE_AUTH_DOMAIN"),
    "databaseURL":       os.getenv("FIREBASE_DATABASE_URL"),
    "projectId":         os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket":     os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId":             os.getenv("FIREBASE_APP_ID"),
}

_REQUIRED_KEYS = ["apiKey", "databaseURL", "projectId"]

def _validate_config():
    missing = [k for k in _REQUIRED_KEYS if not firebase_cfg.get(k)]
    if missing:
        raise EnvironmentError(
            f"Missing required Firebase environment variables: {missing}\n"
            "Copy .env.example → .env and fill in your Firebase project values."
        )

def init_firebase_admin() -> None:
    if firebase_admin._apps:
        return
    _validate_config()
    cred_path = os.path.join(os.path.dirname(__file__), "..", "firebase_credentials.json")
    if not os.path.exists(cred_path):
        raise FileNotFoundError("firebase_credentials.json not found in project root.")
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {"databaseURL": firebase_cfg["databaseURL"]})

def get_admin_auth():
    init_firebase_admin()
    return _admin_auth

def get_db_ref(path: str = "/"):
    init_firebase_admin()
    return _admin_db.reference(path)

_pyrebase_app = None
def get_pyrebase_auth():
    global _pyrebase_app
    _validate_config()
    if _pyrebase_app is None:
        _pyrebase_app = pyrebase.initialize_app(firebase_cfg)
    return _pyrebase_app.auth()

def verify_id_token(id_token: str) -> dict:
    """Verify a Firebase ID token using the Admin SDK."""
    admin_auth = get_admin_auth()
    return admin_auth.verify_id_token(id_token)

def refresh_session_token(refresh_token: str) -> dict:
    """Exchange a refresh token for a new ID token via Pyrebase."""
    pb_auth = get_pyrebase_auth()
    result = pb_auth.refresh(refresh_token)
    return {
        "idToken":      result["idToken"],
        "refreshToken": result["refreshToken"],
        "uid":          result["userId"],
    }

# ── Field definitions ─────────────────────────────────────────────────────────
SERVICE_REQUIRED_FIELDS = ["service_name"]
SERVICE_NUMERIC_FIELDS  = ["response_time", "throughput", "security", "cost"]
SERVICE_ALL_FIELDS      = SERVICE_REQUIRED_FIELDS + SERVICE_NUMERIC_FIELDS + ["timestamp"]

USER_FIELDS = ["uid", "email", "displayName", "createdAt", "lastLoginAt"]


# ── Timestamp helper ──────────────────────────────────────────────────────────
def utc_now() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ══════════════════════════════════════════════════════════════════════════════
# SERVICES
# ══════════════════════════════════════════════════════════════════════════════

def build_service_record(data: dict) -> dict:
    """
    Validate and normalise a raw service dict into the canonical DB schema.

    Required field  : service_name
    Numeric fields  : response_time, throughput, security, cost  (all default to 0.0)
    Auto-generated  : timestamp

    Returns a clean dict ready to push to Firebase.
    Raises ValueError with a descriptive message on invalid input.
    """
    service_name = str(data.get("service_name", "")).strip()
    if not service_name:
        raise ValueError("'service_name' is required and cannot be empty.")

    record = {
        "service_name": service_name,
        "timestamp":    data.get("timestamp") or utc_now(),
    }

    for field in SERVICE_NUMERIC_FIELDS:
        raw = data.get(field, 0)
        try:
            record[field] = float(raw)
        except (TypeError, ValueError):
            raise ValueError(
                f"Field '{field}' must be a number. Got: {raw!r}"
            )

    # Optional range validation
    if not (0 <= record["security"] <= 100):
        raise ValueError("'security' must be between 0 and 100.")
    if record["response_time"] < 0:
        raise ValueError("'response_time' cannot be negative.")
    if record["throughput"] < 0:
        raise ValueError("'throughput' cannot be negative.")
    if record["cost"] < 0:
        raise ValueError("'cost' cannot be negative.")

    return record


def add_service_to_db(uid: str, record: dict) -> dict:
    """
    Push one validated service record to /services/{uid}/ in Realtime DB.
    Returns the stored record with its generated Firebase push-key as 'id'.
    """
    ref     = get_db_ref(f"/services/{uid}")
    new_ref = ref.push(record)
    return {"id": new_ref.key, **record}


def get_services_from_db(uid: str) -> list[dict]:
    """
    Retrieve all service records for the given user from /services/{uid}/.
    Returns a list sorted by timestamp descending (newest first).
    Returns an empty list if no records exist.
    """
    data = get_db_ref(f"/services/{uid}").get() or {}
    services = [{"id": k, **v} for k, v in data.items()]
    # Sort newest first
    services.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
    return services


def delete_service_from_db(uid: str, service_id: str) -> bool:
    """
    Delete the service at /services/{uid}/{service_id}.
    Returns True if it existed and was deleted, False if not found.
    """
    ref = get_db_ref(f"/services/{uid}/{service_id}")
    if ref.get() is None:
        return False
    ref.delete()
    return True


def delete_all_services_from_db(uid: str) -> None:
    """Delete the entire /services/{uid}/ subtree."""
    get_db_ref(f"/services/{uid}").delete()


# ══════════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════════

def update_service_in_db(uid: str, service_id: str, updates: dict) -> dict:
    """
    Update specific fields for an existing service.
    Returns the updated record combined with the ID.
    """
    ref = get_db_ref(f"/services/{uid}/{service_id}")
    if ref.get() is None:
        raise ValueError("Service not found.")
        
    ref.update(updates)
    return {"id": service_id, **ref.get()}

def save_user_to_db(uid: str, email: str, display_name: str) -> None:
    """
    Write (overwrite) a user record at /users/{uid}/.
    Called on first registration.
    """
    get_db_ref(f"/users/{uid}").set({
        "uid":         uid,
        "email":       email,
        "displayName": display_name,
        "createdAt":   utc_now(),
        "lastLoginAt": utc_now(),
    })


def update_user_last_login(uid: str) -> None:
    """Patch only the lastLoginAt field — called on every successful login."""
    try:
        get_db_ref(f"/users/{uid}").update({"lastLoginAt": utc_now()})
    except Exception:
        pass   # non-critical


def get_user_from_db(uid: str) -> dict | None:
    """Fetch user profile from /users/{uid}/. Returns None if not found."""
    return get_db_ref(f"/users/{uid}").get()
