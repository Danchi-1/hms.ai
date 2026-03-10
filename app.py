from flask import Flask, render_template, session, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import db, bcrypt, limiter
from flask_jwt_extended import JWTManager

# Local imports
from api.auth import auth_bp
from api.predict import predict_bp
from api.wearable import wearable_bp
from api.dashboard import dashboard_bp
from api.ai_advice import ai_bp

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Configure Database
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(basedir, 'data', 'sqlite.db')}")
# Quick fix for Render Postgres URLs (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Additional configs for JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key')
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False  # Set to True in production where HTTPS is active
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Disabled for simplicity, can enable later if needed

db.init_app(app)
bcrypt.init_app(app)
limiter.init_app(app)
jwt = JWTManager(app)

# Create tables
with app.app_context():
    db.create_all()

# Configure CORS
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

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(predict_bp, url_prefix='/api/predict')
app.register_blueprint(wearable_bp, url_prefix='/api/wearable')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(ai_bp, url_prefix='/api/ai')

# ---------- ROUTES ----------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/api/health')
def health_check():
    return {
        'status': 'ok',
        'database': 'connected'
    }

# ---------- APP LIFECYCLE ----------

# Note: In production servers like Gunicorn, this might need different handling

@app.teardown_appcontext
def cleanup(error):
    if error:
        print(f"Request error: {error}")



# ---------- ENTRY POINT ----------

if __name__ == '__main__':
    model_path = 'model_training/model.pkl'
    if not os.path.exists(model_path):
        print("Warning: No trained model found.")
        print("Run: python model_training/preprocess.py")
        print("     python model_training/train.py")

    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    print(f"Health Monitoring System starting on port {port}")

    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)
