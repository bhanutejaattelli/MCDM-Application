# 🌐 Dynamic Cloud Service Composition System

> An intelligent cloud service selection platform powered by **Entropy Weight** + **TOPSIS** MCDM algorithms, Firebase Realtime Database, and Firebase Authentication.

---

## 🏗️ Architecture

```
MCDM/
├── backend/
│   ├── app.py             # Flask application entry point
│   ├── auth.py            # Custom Bearer token logic
│   ├── services.py        # Old service algorithms APIs
│   ├── db_routes.py       # Current DB service logic & ranking endpoint
│   ├── algorithm.py       # Pipeline orchestrator
│   ├── entropy_weights.py # Calculates QoS Entropy Weights
│   ├── topsis.py          # TOPSIS Implementation
│   ├── firebase_config.py # Firebase connection logic
│   ├── database.py        # Realtime DB CRUD methods
│   └── config.py          # App constants (QoS configs)
├── frontend_react/
│   ├── src/
│   │   ├── api/           # Axios config injecting Firebase tokens
│   │   ├── components/    # Reusable React components (Charts, Forms)
│   │   ├── context/       # AuthContext for session management
│   │   ├── firebase/      # Firebase Client SDK Config
│   │   ├── pages/         # Dashboard, Login, Register Views
│   │   ├── App.jsx        # Routing configuration
│   │   └── index.css      # Tailwind core CSS
│   ├── tailwind.config.js # Tailwind V3 configuration
│   └── package.json       # Frontend dependencies
├── .env.example           # Environment variables template
├── requirements.txt       # Python dependencies
└── README.md
```

---

## Features
- **Firebase Authentication** (Email & Password)
- **Firebase Realtime Database** for seamless cloud data storage
- **React.js Dashboard** with Tailwind CSS and Recharts visualizations
- **Flask REST API** handling heavy computation
- **MCDM Algorithms**:
  - Fuzzy Entropy Weight Method (Objective weights determination)
  - TOPSIS Method (Ranking alternatives)

---

## ⚙️ Prerequisites

| Requirement | Version |
|---|---|
| Python | **3.10** or higher |
| pip | 23+ |
| Node.js | 18+ |
| npm | 9+ |
| Firebase project | Realtime Database + Authentication enabled |

---

## 🔑 Firebase Setup

### Step 1 — Create a Firebase project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. **Create Project** → name it (e.g. `cloud-mcdm`)
3. Enable **Authentication**: *Sign-in method* → **Email/Password** ✅
4. Enable **Realtime Database**: *Build* → *Realtime Database* → Create database (start in **test mode** for dev)

### Step 2 — Get the Web Config

Firebase Console → **Project Settings** → **General** → scroll to *Your apps* → click `</>` (Web) → copy the config object:

```json
{
  "apiKey": "AIzaSy...",
  "authDomain": "your-project.firebaseapp.com",
  "databaseURL": "https://your-project-default-rtdb.firebaseio.com",
  "projectId": "your-project",
  "storageBucket": "your-project.appspot.com",
  "messagingSenderId": "1234567890",
  "appId": "1:1234567890:web:abc123"
}
```

### Step 3 — Download Service Account Key (for Admin SDK)

Firebase Console → **Project Settings** → **Service Accounts** → **Generate new private key** → save as **`firebase_credentials.json`** in the project root.

> ⚠️ Never commit `firebase_credentials.json` or `.env` to git.

### Step 4 — Set Realtime Database Rules (development)

```json
{
  "rules": {
    ".read":  "auth != null",
    ".write": "auth != null"
  }
}
```

---

## 🛠️ Environment Setup

### 1. Clone / open the project

```powershell
cd "d:\Major Project\MCDM"
```

### 2. Create virtual environment (Python Backend)

```powershell
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
```

### 3. Install dependencies (Python Backend)

```powershell
pip install -r requirements.txt
```

### 4. Frontend Environment (React.js)
```bash
cd frontend_react
npm install
# Create an .env.local file in frontend_react with your Firebase keys based on the backend .env
```

### 5. Configure environment variables

```powershell
copy .env.example .env
```

Open `.env` and fill in your real Firebase values:

```env
FIREBASE_API_KEY=AIzaSy...
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com
FIREBASE_PROJECT_ID=your-project
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=1234567890
FIREBASE_APP_ID=1:1234567890:web:abc123

FIREBASE_CREDENTIALS_PATH=firebase_credentials.json
FLASK_SECRET_KEY=replace-with-a-long-random-string
FLASK_PORT=5000
FLASK_DEBUG=False
BACKEND_URL=http://localhost:5000
```

### 6. Place firebase_credentials.json

Put your downloaded service account key at:
```
d:\Major Project\MCDM\firebase_credentials.json
```

---

## 🚀 Running the Application

### 1. Start the Flask Backend

Open a terminal and run:
```powershell
cd "d:\Major Project\MCDM"
venv\Scripts\activate
python backend\app.py
```

### 2. Start the React Frontend

Open a new terminal and run the Vite development server:
```bash
cd frontend_react
npm run dev
```

The application will be available at [`http://localhost:5173`](http://localhost:5173).

### Verify

| Service | URL | Expected |
|---|---|---|
| Flask health check | http://localhost:5000/health | `{"status":"ok"}` |
| React UI | http://localhost:5173 | Login page |

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create new user |
| POST | `/auth/login` | Email/password login |
| POST | `/auth/logout` | Revoke tokens |
| GET  | `/auth/verify` | Verify token |

### Services
| Method | Endpoint | Description |
|---|---|---|
| POST | `/services/upload` | Upload Excel file |
| POST | `/services/manual` | Bulk manual entry |
| GET  | `/services/list` | List all services |
| POST | `/services/rank` | Run ranking algorithm |
| DELETE | `/services/all` | Delete all services |

### Database (new endpoints)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/add_service` | Add single service |
| GET  | `/get_services` | Retrieve services (supports `?sort_by&order&limit`) |
| DELETE | `/delete_service/<id>` | Delete one service |

> All endpoints except `/auth/*` require: `Authorization: Bearer <idToken>`

---

## 📊 Database Schema

```
Firebase Realtime Database
│
├── users/
│   └── {uid}/
│       ├── email
│       ├── displayName
│       ├── createdAt
│       └── lastLoginAt
│
└── services/
    └── {uid}/
        └── {push_id}/
            ├── service_name    (string)
            ├── response_time   (float, ms)
            ├── throughput      (float, req/s)
            ├── security        (float, 0-100)
            ├── cost            (float, USD/mo)
            └── timestamp       (ISO-8601 UTC)
```

---

## 🧮 Algorithm Pipeline

```
  Raw QoS Data  (m services × 4 criteria)
        │
        ▼
  entropy_weights.py
  ┌─────────────────────────────────┐
  │ Step 1: Normalize (min-max)     │
  │ Step 2: Probability matrix      │
  │ Step 3: Shannon entropy E_j     │
  │ Step 4: Divergence d_j = 1-E_j  │
  │ Step 5: Weights w_j = d_j/Σd_k  │
  └─────────────────────────────────┘
        │  weights[]
        ▼
  topsis.py
  ┌─────────────────────────────────┐
  │ Step 1: Vector normalization    │
  │ Step 2: Weighted matrix v_ij    │
  │ Step 3: Positive Ideal (V+)     │
  │ Step 4: Negative Ideal (V-)     │
  │ Step 5: Euclidean D+, D-        │
  │ Step 6: CC = D- / (D+ + D-)    │
  │ Step 7: Rank by CC desc         │
  └─────────────────────────────────┘
        │
        ▼
  Ranked Services + Best Recommendation
```

---

## 🛡️ Security Notes

- `.env` and `firebase_credentials.json` are excluded from version control
- All API endpoints validate Firebase ID tokens server-side
- Realtime Database rules enforce per-user data isolation
- Tokens are revoked server-side on logout

---

## 🐛 Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Package missing | `pip install -r requirements.txt` |
| `firebase_admin.exceptions` | Missing credentials | Put `firebase_credentials.json` in project root |
| `ConnectionError` from Streamlit | Flask not running | Start Flask first in another terminal |
| `400 INVALID_EMAIL` on login | Wrong Firebase API key | Check `FIREBASE_API_KEY` in `.env` |
| Blank Realtime DB | DB rules too strict | Set rules to `auth != null` while testing |
| `ValueError: At least 2 services` | Too few services stored | Add at least 2 services before ranking |

---

## 📁 .gitignore Recommendations

```gitignore
# Environment & secrets
.env
firebase_credentials.json

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
venv/
.venv/

# Streamlit cache
.streamlit/

# IDE
.vscode/
.idea/
```
