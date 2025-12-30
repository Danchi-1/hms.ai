from flask import Flask, render_template, session, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Local imports
from services.background_manager import BackgroundServiceManager
from api.auth import auth_bp
from api.predict import predict_bp
from api.wearable import wearable_bp
from api.dashboard import dashboard_bp
from api.ai_advice import ai_bp

# Initialize background services
background_manager = BackgroundServiceManager()

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

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
        'database': 'connected',
        'services': {
            'running': background_manager.is_running
        }
    }

# ---------- APP LIFECYCLE ----------

# Note: In production servers like Gunicorn, this might need different handling
# But for local dev/demo, we can start services on first request or main

def start_services():
    background_manager.start_services()

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
    
    # Start background services
    start_services()

    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)
