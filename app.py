from flask import Flask, render_template, redirect, url_for, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
import sys
from datetime import timedelta

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import db, bcrypt, limiter, User
from flask_jwt_extended import JWTManager

# Local imports
from api.auth import auth_bp
from api.predict import predict_bp
from api.wearable import wearable_bp
from api.dashboard import dashboard_bp
from api.ai_advice import ai_bp
from api.emergency import emergency_bp
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
import json

# Initialize Flask app
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

app.secret_key = os.getenv('SECRET_KEY', 'hms-ai-super-secret-key-change-in-production')

# ── Database ──────────────────────────────────────────────────────────────────
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(basedir, 'data', 'sqlite.db')}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── JWT Configuration ─────────────────────────────────────────────────────────
is_production = os.getenv('FLASK_ENV', 'development') == 'production'
is_debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'hms-jwt-secret-2024-change-in-production')
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = is_production          # True on Render (HTTPS only)
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

db.init_app(app)
bcrypt.init_app(app)
limiter.init_app(app)
jwt = JWTManager(app)

# ── Dev account seeding ───────────────────────────────────────────────────────
def seed_dev_account():
    """Create the developer account on startup if it doesn't already exist."""
    dev_email    = os.getenv('DEV_EMAIL')
    dev_password = os.getenv('DEV_PASSWORD')
    dev_username = os.getenv('DEV_USERNAME')
    if not (dev_email and dev_password and dev_username):
        return
    if User.query.filter_by(email=dev_email).first():
        return  # already exists
    pw_hash = bcrypt.generate_password_hash(dev_password).decode('utf-8')
    db.session.add(User(username=dev_username, email=dev_email, password_hash=pw_hash))
    db.session.commit()
    print(f"[HMS-AI] Dev account seeded: {dev_email}")

with app.app_context():
    db.create_all()
    seed_dev_account()

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://hmsai.vercel.app",
            "https://hmsai.onrender.com",
            "http://localhost:5000",
            "http://127.0.0.1:5000"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
}, supports_credentials=True)

# ── HTTPS Enforcement (Render / production load-balancer) ─────────────────────
@app.before_request
def enforce_https():
    """Redirect HTTP → HTTPS when running behind Render's load balancer."""
    if is_production and request.headers.get('X-Forwarded-Proto') == 'http':
        return redirect(request.url.replace('http://', 'https://', 1), code=301)

# ── Register blueprints ───────────────────────────────────────────────────────
app.register_blueprint(auth_bp,      url_prefix='/api/auth')
app.register_blueprint(predict_bp,   url_prefix='/api/predict')
app.register_blueprint(wearable_bp,  url_prefix='/api/wearable')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(ai_bp,        url_prefix='/api/ai')
app.register_blueprint(emergency_bp, url_prefix='/api/emergency')

# ── Page routes ───────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login_page():
    try:
        verify_jwt_in_request(optional=True)
        raw_user = get_jwt_identity()
        if json.loads(raw_user) if raw_user else None:
            return redirect(url_for('dashboard_page'))
    except Exception:
        pass
    # Pass dev_email only in debug mode — renders the quick-login button
    dev_email = os.getenv('DEV_EMAIL') if is_debug else None
    return render_template('login.html', dev_email=dev_email)

@app.route('/signup')
def signup_page():
    try:
        verify_jwt_in_request(optional=True)
        raw_user = get_jwt_identity()
        if json.loads(raw_user) if raw_user else None:
            return redirect(url_for('dashboard_page'))
    except Exception:
        pass
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard_page():
    try:
        verify_jwt_in_request(optional=True)
        raw_user = get_jwt_identity()
        current_user = json.loads(raw_user) if raw_user else None
        if not current_user:
            return redirect(url_for('login_page'))
    except Exception:
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    response = redirect(url_for('login_page'))
    response.set_cookie('access_token_cookie', '', expires=0)
    response.set_cookie('refresh_token_cookie', '', expires=0)
    return response

@app.route('/api/health')
def health_check():
    return {'status': 'ok', 'database': 'connected'}

# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.teardown_appcontext
def cleanup(error):
    if error:
        print(f"Request error: {error}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"HMS-AI starting on port {port} | debug={is_debug} | production={is_production}")
    app.run(host='0.0.0.0', port=port, debug=is_debug, threaded=True)
