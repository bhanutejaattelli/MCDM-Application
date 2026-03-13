# 🌐 Dynamic Cloud Service Composition System

An intelligent cloud service selection platform powered by **Entropy Weight** + **TOPSIS** MCDM algorithms, Firebase Realtime Database, and Firebase Authentication.

---

## 🏗️ Architecture (Monorepo)

```
MCDM/
├── backend/               # Flask API (Serverless compatible)
│   ├── app.py             # Application factory & entry point
│   ├── auth.py            # Firebase Auth logic & routes
│   ├── services.py        # Service CRUD & Ranking routes
│   ├── database.py        # Firebase Realtime DB helpers
│   └── algorithm.py       # Unified MCDM (Entropy + TOPSIS) logic
├── frontend/              # React + Vite Application
│   ├── src/
│   │   ├── components/    # UI Components (Charts, Forms, Tables)
│   │   ├── pages/         # View Pages (Dashboard, Login, Register)
│   │   └── App.jsx        # Root routing & API client config
├── vercel.json            # Unified Vercel deployment config
├── package.json           # Root monorepo build config
├── requirements.txt       # Python backend dependencies
└── README.md
```

---

## 📡 Standardized API Endpoints

All data is now consolidated under the `/api` prefix (managed by Vercel rewrites).

### Authentication (`/api/auth`)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/register` | Create a new user account |
| POST | `/login` | Sign in and retrieve ID Token |
| POST | `/logout` | Revoke sessions and logout |
| GET  | `/profile` | Fetch user profile data |

### Services (`/api/services`)
| Method | Endpoint | Description |
|---|---|---|
| GET  | `/` | List services (supports search, sort, pagination) |
| POST | `/manual` | Add a new cloud service manually |
| POST | `/upload` | Bulk upload services via Excel (.xlsx) |
| POST | `/rank` | Execute Entropy Weight + TOPSIS ranking |
| PUT  | `/<id>` | Update QoS parameters for a service |
| DELETE | `/<id>` | Delete a specific service |
| DELETE | `/` | Clear all stored services |

---

## 🚀 Execution Guide

### Local Development
1. **Backend**: Run `start_backend.bat` to launch the Flask server on port 5000.
2. **Frontend**: Run `start_frontend.bat` to launch the Vite dev server.
3. Open [`http://localhost:5173`](http://localhost:5173).

### Deployment (Vercel)
The project is "push-to-deploy" ready:
1. Connect your repository to Vercel.
2. Set `FIREBASE_SERVICE_ACCOUNT_JSON` and other environment variables in the Vercel Dashboard.
3. Deployment is automatic on every push to `main`.

---

## 🧮 Algorithm Details
The system utilizes a hybrid MCDM approach:
1. **Entropy Weight Method**: Dynamically calculates importance weights based on the data variance of QoS parameters.
2. **TOPSIS**: Ranks services by calculating their geometric distance to the ideal (best) and anti-ideal (worst) solutions.
