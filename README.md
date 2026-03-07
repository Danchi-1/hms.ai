# HMS-AI — Health Monitoring System

**HMS-AI** is an AI-powered health analytics platform that collects, visualizes, and analyzes data from Bluetooth wearable devices in real time. It combines a modern dark-themed web interface with machine learning insights to give users a personalized picture of their health.

---

## 🚀 Features

| Feature | Status | Notes |
|:---|:---:|:---|
| **User Authentication** | ✅ | Login/Signup with SHA256 hashing, Flask session management, profile chip in header |
| **Real-time Dashboard** | ✅ | Heart Rate, Steps, Sleep, Calories via Chart.js — only populated from real device data |
| **Web Bluetooth Integration** | ✅ | Browser-native BLE via the Web Bluetooth API — no server required |
| **AI Health Score** | ✅ | 0–100 score aggregated from vitals with confidence levels and personalized insights |
| **ML Recommendations** | ✅ | Scikit-learn RandomForest classifier in `api/predict.py` generates context-aware advice |
| **Vital Signs Monitoring** | ✅ | Live heart rate from GATT notifications; BP / SpO₂ / temp shown only with real sensor data |
| **Sleep Analysis** | ✅ | 7-day sleep chart (hours + efficiency) rendered via Chart.js |
| **Data Export** | ✅ | Full CSV export of health metrics via `/api/wearable/data/export` |
| **Responsive UI** | ✅ | Glassmorphism dark theme, mobile-first layout, split-panel auth pages |
| **Hybrid Deployment** | ✅ | Vercel (frontend CDN) + Render (Flask/Gunicorn backend) |

---

## 🔵 Bluetooth Architecture

HMS-AI uses two complementary Bluetooth integrations:

### Web Bluetooth API (Primary — browser-side)
The main way users connect wearables. Runs entirely in the browser — no server
Bluetooth adapter needed.

```
User's Browser (Chrome/Edge)
  └── navigator.bluetooth.requestDevice()
        └── Native OS device picker shown to user
              └── User selects their wearable
                    ├── Read: battery level, manufacturer name
                    └── Subscribe: heart rate notifications (live, every ~1 s)
                          ├── Updates dashboard metrics in real time
                          └── POST /api/wearable/ble-reading → persisted to DB
```

**Requirements:**
- HTTPS (or `localhost`) — Web Bluetooth is blocked on plain HTTP
- Chrome 56+ / Edge 79+ / Opera 43+ — Firefox and Safari are not supported
- A user gesture (button click) to trigger the device picker

**Supported devices** (anything advertising standard GATT services):
`Polar · Garmin · Fitbit · Samsung Galaxy Watch · Mi Band · Amazfit · WHOOP · Oura Ring`
…plus any device advertising Heart Rate (`0x180D`), Blood Pressure (`0x1810`), Fitness Machine (`0x1826`), or Glucose (`0x1808`) services.

### Python `bleak` Library (Secondary — server-side)
Located in `ble/ble.py`. Useful when the Flask server is running **locally** on the same machine as the wearable device (e.g. a Raspberry Pi, a development laptop).

> ⚠️ The `bleak` backend is **not** called by the web dashboard on cloud deployments (Render/Vercel) because the server has no physical Bluetooth adapter that can reach the user's device.

---

## 🎨 Frontend Design System

The UI was redesigned in March 2026 with a new medical-tech aesthetic.

| Token | Value |
|---|---|
| **Background** | `#060c18` / `#0a0f1c` (deep charcoal) |
| **Accent Primary** | `#0d9488` (medical teal) |
| **Accent Secondary** | `#10b981` (emerald green) |
| **Font** | Inter (variable weight) |
| **Cards** | Glassmorphism — `backdrop-filter: blur(20px)` + subtle teal border glow |
| **Buttons** | Pill-shaped, gradient fill, shimmer-on-hover |

**Page layouts:**
- **Landing page** — Split-panel hero (copy left, live health card mock right), stats bar, feature cards, timeline steps, device logos
- **Login / Sign Up** — Split-panel (decorative left with stats + form right)
- **Dashboard** — 3-column responsive card grid with glassmorphism cards

---

## 🛠 Tech Stack

### Frontend
- **HTML5 / CSS3 / Vanilla JS (ES6+)**
- **Web Bluetooth API** — browser-native BLE device connection
- **Chart.js** — sleep trend charts
- **Font Awesome 6** — icons
- **Google Fonts** — Inter

### Backend
- **Flask** (Python 3.12+)
- **Pandas / NumPy** — data processing
- **Scikit-learn** — RandomForest health risk prediction
- **SQLite** (dev) / ephemeral cloud DB (prod)
- **Flask-CORS** — cross-origin headers for Vercel ↔ Render

### Infrastructure
- **Vercel** — frontend (global CDN, rewrite rules)
- **Render** — backend (Gunicorn WSGI)
- **Docker** — containerized production build
- **Git** — CI/CD via push-triggered deployments

---

## 📂 Project Structure

```
hms.ai/
├── api/
│   ├── auth.py          # Login, Register, Profile (/api/auth/*)
│   ├── dashboard.py     # Data aggregation (/api/dashboard/<user_id>)
│   ├── predict.py       # ML inference (/api/predict/*)
│   ├── wearable.py      # Data export, BLE reading ingestion
│   └── ai_advice.py     # Gemini AI health advice (/api/ai/*)
├── ble/
│   └── ble.py           # Python BLE scanner (bleak) — local/Pi use
├── database/
│   └── models.py        # User & HealthData SQLite models
├── model_training/
│   ├── preprocess.py    # Dataset preparation
│   └── train.py         # Train RandomForest health risk model
├── services/
│   └── background_manager.py  # Background data collection services
├── static/
│   ├── css/
│   │   ├── main.css     # Design tokens, navbar, buttons, footer
│   │   ├── home.css     # Landing page styles (hero, features, steps)
│   │   ├── auth.css     # Login/signup split-panel styles
│   │   └── dashboard.css # Dashboard card grid and metric styles
│   └── js/
│       ├── main.js      # Auth forms, mobile nav, loading spinner
│       └── dashboard.js # Dashboard data loading, Web Bluetooth, charts
├── templates/
│   ├── index.html       # Landing page
│   ├── login.html       # Login page
│   ├── signup.html      # Sign up page
│   └── dashboard.html   # Main dashboard
├── app.py               # Flask entry point, route definitions
├── Dockerfile           # Production container
├── requirements.txt     # Python dependencies
└── vercel.json          # Vercel routing/rewrite rules
```

---

## 🔧 Setup & Installation

### Prerequisites
- Python 3.12+
- pip
- A Chromium-based browser (Chrome / Edge) for Bluetooth features

### Local Development

```bash
# 1. Clone
git clone https://github.com/Danchi-1/hms.ai.git
cd hms.ai

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY and GEMINI_API_KEY

# 5. (Optional) Train the ML model
python model_training/preprocess.py
python model_training/train.py

# 6. Run
python app.py
```

Visit `http://localhost:5000` — Bluetooth features work on localhost without HTTPS.

### Deployment

| Platform | Config |
|---|---|
| **Render (backend)** | Build: `pip install -r requirements.txt` · Start: `gunicorn app:app` |
| **Vercel (frontend)** | Framework: `Other` · Ensure `vercel.json` rewrites are present |
| **Docker** | `docker build -t hms-ai . && docker run -p 5000:5000 hms-ai` |

> ⚠️ On cloud deployments, the app **must** be served over HTTPS for Web Bluetooth to work. Render and Vercel both provide HTTPS by default.

---

## 🧪 ML & AI Integration

| Component | Details |
|---|---|
| **Model** | `RandomForestClassifier` (Scikit-learn) |
| **Inputs** | Steps, sleep duration, sleep efficiency, heart rate |
| **Output** | Risk level (Low / Medium / High) + confidence score |
| **Inference** | Runs on dashboard load via `/api/predict/` |
| **AI Advice** | Gemini API (`/api/ai/health-advice`) generates natural-language recommendations |
| **Training** | `python model_training/train.py` — saves `model.pkl` |

---

## 📊 Dashboard Data Policy

**No data is ever simulated or fabricated.** All metric cards (`--` by default) update only from two real sources:

1. **Backend API** — historical data from `/api/dashboard/<user_id>` (Fitbit sync data stored in DB)
2. **Web Bluetooth** — live readings from a physically connected BLE device (heart rate notifications via GATT)

Vitals such as blood pressure, SpO₂, and temperature remain at `--` until a compatible sensor provides them. Trend indicators are only shown with real historical comparison data.

---

## 🔐 Security

- **Passwords**: SHA256 with salt via `hashlib`
- **Sessions**: Flask `session` encrypted with `SECRET_KEY`
- **Input validation**: Regex sanitization on username/email fields
- **CORS**: Strict origin whitelist (Vercel + Render + localhost only)
- **Bluetooth**: Browser enforces HTTPS-only access and explicit user permission per device

---

## 🌐 Browser Compatibility

| Feature | Chrome | Edge | Firefox | Safari |
|---|:---:|:---:|:---:|:---:|
| General UI | ✅ | ✅ | ✅ | ✅ |
| Web Bluetooth | ✅ | ✅ | ❌ | ❌ |
| Chart.js | ✅ | ✅ | ✅ | ✅ |

For full functionality (Bluetooth device connection), use **Chrome or Edge**.

---

## 📄 License

MIT License — see `LICENSE` for details.
