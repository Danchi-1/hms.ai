# Health Monitoring System (HMS.AI)

**HMS.AI** is an advanced health analytics platform designed to collect, visualize, and analyze data from wearable devices. It combines a modern, responsive web interface with machine learning data analysis to provide actionable health insights.

## 🚀 Key Features & Achievements

| Feature | Goal | Current Achievement |
|:---|:---|:---|
| **User Authentication** | Secure, seamless access control. | ✅ **Implemented**: Login/Signup with SHA256 password hashing, session management, and "Remember Me" functionality. includes a personalized "Profile Chip" in the header. |
| **Interactive Dashboard** | Real-time visualization of health metrics. | ✅ **Implemented**: Dynamic dashboard displaying Heart Rate, Steps, Sleep Quality, and Calories using Chart.js. Includes auto-refresh logic and error handling. |
| **AI Health Score** | Quantifiable health metric based on data. | ✅ **Implemented**: Custom algorithm that aggregates vital signs into a 0-100 "Health Score" with personalized insights and confidence levels. |
| **ML-Driven Recommendations** | Actionable advice based on user data. | ✅ **Implemented**: Scikit-learn integration (`api/predict.py`) that analyzes user vitals to generate context-aware health tips (e.g., "Improve sleep efficiency"). |
| **Wearable Connectivity** | Connect to BLE devices. | ✅ **Simulated**: "Connect Closest Device" feature (`/api/wearable/connect-closest`) simulates BLE scanning and RSSI signal strength detection. |
| **Data Export** | allow users to own their data. | ✅ **Implemented**: Full CSV export functionality for health metrics (`/api/wearable/data/export`). |
| **Responsive UI/UX** | Premium experience across devices. | ✅ **Implemented**: Glassmorphism-inspired dark UI, fully responsive Mobile Hamburger Menu, and smooth CSS animations. |
| **Hybrid Deployment** | Scalable, cost-effective hosting. | ✅ **Implemented**: Frontend deployed on **Vercel** (Global CDN) communicating with a **Render** (Python/Flask) backend. |

---

## 🛠 Tech Stack

### Frontend
- **Core**: HTML5, CSS3 (Custom Glassmorphism Design), Vanilla JavaScript (ES6+).
- **Visualization**: Chart.js for interactive health graphs.
- **Routing**: Client-side routing logic for SPA-like experience on Vercel.

### Backend
- **Framework**: Flask (Python 3.12).
- **Data Processing**: Pandas, NumPy.
- **Machine Learning**: Scikit-Learn (RandomForest, GradientBoosting for risk prediction).
- **Database**: SQLite (Development) / Ephemeral (Cloud).
- **Communication**: REST API with structured JSON responses.

### Infrastructure
- **Containerization**: Docker (optimized build).
- **Hosting**:
    - **Frontend**: Vercel (Static hosting with Rewrite rules).
    - **Backend**: Render (Gunicorn WSGI server).
- **CI/CD**: Git-based deployment triggers.
- **Optimization**: Aggressive cache-busting (`?v=3.1`) for asset updates.

---

## 📂 Project Structure

```
hms.ai/
├── api/                 # Flask Blueprints (API endpoints)
│   ├── auth.py          # Login, Register, Profile management
│   ├── dashboard.py     # Dashboard data aggregation
│   ├── predict.py       # ML Model inference endpoints
│   └── wearable.py      # BLE connectivity & Data export
├── database/            # Database logic
│   └── models.py        # User & HealthData models (SQLite)
├── model_training/      # ML Pipeline
│   └── train.py         # Script to train/optimize Health AI models
├── static/              # Static Assets
│   ├── css/             # Main.css (Responsive design)
│   └── js/              # Main.js, Dashboard.js (Frontend logic)
├── templates/           # HTML Templates (Jinja2 compatible)
├── app.py               # Main Flask Application Entry Point
├── Dockerfile           # Production container configuration
├── requirements.txt     # Python dependencies (Optimized)
└── vercel.json          # Vercel routing configuration
```

---

## 🔧 Setup & Installation

### Local Development

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Danchi-1/hms.ai.git
    cd hms.ai
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set Environment Variables**
    Create a `.env` file:
    ```env
    SECRET_KEY=your_secret_key
    FLASK_DEBUG=1
    PORT=5000
    ```

4.  **Run the Application**
    ```bash
    python app.py
    ```
    Visit `http://localhost:5000` in your browser.

### Deployment

-   **Backend (Render)**: Connect repo to Render. Set Build Command: `pip install -r requirements.txt`, Start Command: `gunicorn app:app`.
-   **Frontend (Vercel)**: Import repo to Vercel. Select `Other` framework. Ensure `vercel.json` exists for routing.

---

## 🧪 AI & Machine Learning Integration

The system uses a **Random Forest Classifier** trained on health metrics (Steps, Sleep, Heart Rate, etc.) to predict potential health risks.

-   **Training**: `python model_training/train.py`
-   **Inference**: The model is loaded at startup. When the dashboard loads, it feeds user data into the model to generate a "Risk Level" and "Confidence Score".
-   **Recommendations**: Rule-based logic supplements the ML model to provide immediate, explainable advice.

---

## 🔐 Security Measures

-   **Password Hashing**: SHA256 via `hashlib` (Salted).
-   **Session Security**: Flask `session` with secret key encryption.
-   **Input Validation**: Regex sanitization for Usernames and Emails.
-   **CORS Policy**: Strict Origin access control for Vercel/Render communication.

---

## 📄 License
This project is licensed under the MIT License.
