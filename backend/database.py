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
│       ├── role          : string  ("user" | "admin")
│       ├── createdAt     : ISO-8601 string (UTC)
│       └── lastLoginAt   : ISO-8601 string (UTC)
│
├── services/
│   └── {uid}/
│       └── {push_id}/
│           ├── service_name  : string          — Cloud provider / service label
│           ├── response_time : float  (ms)     — Average latency (lower = better)
│           ├── throughput    : float  (req/s)  — Requests per second (higher = better)
│           ├── security      : float  (0-100)  — Security score (higher = better)
│           ├── cost          : float  (USD/mo) — Monthly cost (lower = better)
│           └── timestamp     : string (ISO-8601 UTC) — When the record was added
│
├── global_providers/
│   └── {provider_id}/
│       ├── name          : string          — Service name (e.g. "AWS EC2 t3.micro")
│       ├── provider      : string          — Cloud provider (AWS | Azure | GCP)
│       ├── type          : string          — Service type (Compute | Storage | Database | Network)
│       ├── cost          : float  (USD/hr) — Hourly cost
│       ├── response_time : float  (ms)     — Estimated latency
│       ├── throughput    : float  (req/s)  — Estimated throughput
│       ├── security      : float  (0-10)   — Estimated security score
│       └── last_updated  : string (ISO-8601 UTC)
│
└── update_logs/
    └── {push_id}/
        ├── timestamp     : string (ISO-8601 UTC)
        ├── status        : string ("success" | "error")
        ├── message       : string
        ├── aws_count     : int
        ├── azure_count   : int
        └── gcp_count     : int
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
    
    # Try loading from Environment Variable (for Vercel)
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        import json
        try:
            cred_dict = json.loads(service_account_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {"databaseURL": firebase_cfg["databaseURL"]})
            return
        except Exception as e:
            print(f"Failed to initialize Firebase from env var: {e}")

    # Fallback to local file (for local development)
    cred_path = os.path.join(os.path.dirname(__file__), "..", "firebase_credentials.json")
    if not os.path.exists(cred_path):
        raise FileNotFoundError(
            "Firebase credentials not found. Set FIREBASE_SERVICE_ACCOUNT_JSON env var "
            "or ensure firebase_credentials.json exists in project root."
        )
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

USER_FIELDS = ["uid", "email", "displayName", "role", "createdAt", "lastLoginAt"]


# ── Timestamp helper ──────────────────────────────────────────────────────────
def utc_now() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ══════════════════════════════════════════════════════════════════════════════
# SERVICES (per-user)
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
    Called on first registration. Sets role to 'user' by default.
    """
    get_db_ref(f"/users/{uid}").set({
        "uid":         uid,
        "email":       email,
        "displayName": display_name,
        "role":        "user",
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


# ── Role-Based Access Control helpers ─────────────────────────────────────────

def get_user_role(uid: str) -> str:
    """Return user's role ('admin' or 'user'). Defaults to 'user' if not set."""
    user = get_db_ref(f"/users/{uid}").get()
    if user and isinstance(user, dict):
        return user.get("role", "user")
    return "user"


def set_user_role(uid: str, role: str) -> None:
    """Update a user's role in the database."""
    if role not in ("user", "admin"):
        raise ValueError("Role must be 'user' or 'admin'.")
    get_db_ref(f"/users/{uid}").update({"role": role})


def get_all_users() -> list[dict]:
    """Return all user records from /users/. For admin user listing."""
    data = get_db_ref("/users").get() or {}
    users = []
    for uid, user_data in data.items():
        if isinstance(user_data, dict):
            users.append({"uid": uid, **user_data})
    return users


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL PROVIDERS
# ══════════════════════════════════════════════════════════════════════════════

def add_global_provider(record: dict) -> dict:
    """Push a provider record to /global_providers/. Returns record with id."""
    ref = get_db_ref("/global_providers")
    new_ref = ref.push(record)
    return {"id": new_ref.key, **record}


def get_global_providers() -> list[dict]:
    """Retrieve all global providers from /global_providers/."""
    data = get_db_ref("/global_providers").get() or {}
    providers = []
    for k, v in data.items():
        if isinstance(v, dict):
            providers.append({"id": k, **v})
    return providers


def update_global_provider(provider_id: str, updates: dict) -> dict:
    """Update fields for a global provider. Returns the updated record."""
    ref = get_db_ref(f"/global_providers/{provider_id}")
    if ref.get() is None:
        raise ValueError("Global provider not found.")
    ref.update(updates)
    return {"id": provider_id, **ref.get()}


def delete_global_provider(provider_id: str) -> bool:
    """Delete a global provider by ID. Returns True if deleted."""
    ref = get_db_ref(f"/global_providers/{provider_id}")
    if ref.get() is None:
        return False
    ref.delete()
    return True


def delete_all_global_providers() -> None:
    """Delete the entire /global_providers/ subtree."""
    get_db_ref("/global_providers").delete()


def set_global_provider(provider_id: str, record: dict) -> dict:
    """Set (overwrite) a global provider at a specific ID."""
    get_db_ref(f"/global_providers/{provider_id}").set(record)
    return {"id": provider_id, **record}


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE LOGS
# ══════════════════════════════════════════════════════════════════════════════

def add_update_log(log_entry: dict) -> dict:
    """Push an update log entry to /update_logs/."""
    log_entry["timestamp"] = utc_now()
    ref = get_db_ref("/update_logs")
    new_ref = ref.push(log_entry)
    return {"id": new_ref.key, **log_entry}


def get_update_logs(limit: int = 20) -> list[dict]:
    """Retrieve recent update logs, newest first."""
    data = get_db_ref("/update_logs").get() or {}
    logs = []
    for k, v in data.items():
        if isinstance(v, dict):
            logs.append({"id": k, **v})
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs[:limit]
