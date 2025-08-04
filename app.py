from flask import Flask, request, jsonify, session, send_from_directory, redirect, url_for
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
import os
import sys
import threading
import time

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Local imports
from model_training.preprocess import HealthDataPreprocessor
from database.models import DatabaseManager
from ble.ble import BLEHealthMonitor
from collector.collector import HealthDataCollector
from model_training.train import HealthAITrainer
from api.auth import auth_bp, login, register
from api.predict import predict_bp
from api.wearable import wearable_bp

# Pre-initialize components
preprocessor = HealthDataPreprocessor()
preprocessor.preprocess_data()
db_manager = DatabaseManager(db_path="data/sqlite.db")
data_collector = HealthDataCollector(db_manager)
train_model = HealthAITrainer()
ble_scanner = BLEHealthMonitor()
background_threads = []

# Initialize Flask app
app = Flask(
    __name__,
    static_folder='frontend',
    static_url_path=''
)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Enable CORS
CORS(app, supports_credentials=True)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(predict_bp, url_prefix='/api/predict')
app.register_blueprint(wearable_bp, url_prefix='/api/wearable')


# ---------- ROUTES ----------

@app.route('/')
def home():
    return send_from_directory('frontend', 'index.html')

@app.route('/login')
def login_page():
    return send_from_directory('frontend', 'login.html')

@app.route('/signup')
def signup_page():
    return send_from_directory('frontend', 'signup.html')

@app.route('/dashboard')
def dashboard_page():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return send_from_directory('frontend', 'dashboard.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if login(email, password):
        session['user'] = email
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid credentials'})


@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    if register(data):
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Signup failed'})


@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'database': 'connected',
        'services': {
            'ble_scanner': ble_scanner.is_scanning if ble_scanner else False,
            'data_collector': data_collector.is_processing if data_collector else False
        }
    })


@app.route('/api/dashboard/<int:user_id>')
def dashboard(user_id):
    try:
        health_data = db_manager.get_user_health_data(user_id, days=7)

        activity_summary = {}
        if health_data['activity']:
            recent = health_data['activity'][:7]
            activity_summary = {
                'avg_steps': sum(a['total_steps'] for a in recent) / len(recent),
                'avg_calories': sum(a['calories'] for a in recent) / len(recent),
                'avg_active_minutes': sum(a['very_active_minutes'] + a['fairly_active_minutes'] for a in recent) / len(recent)
            }

        sleep_summary = {}
        if health_data['sleep']:
            recent = health_data['sleep'][:7]
            sleep_summary = {
                'avg_sleep_duration': sum(s['total_minutes_asleep'] for s in recent) / len(recent),
                'avg_sleep_efficiency': sum(s['sleep_efficiency'] for s in recent) / len(recent)
            }

        heart_rate_summary = {}
        if health_data['heart_rate']:
            recent = health_data['heart_rate'][-100:]
            heart_rate_summary = {
                'avg_heart_rate': sum(h['heart_rate'] for h in recent) / len(recent),
                'max_heart_rate': max(h['heart_rate'] for h in recent),
                'min_heart_rate': min(h['heart_rate'] for h in recent)
            }

        return jsonify({
            'user_id': user_id,
            'summary': {
                'activity': activity_summary,
                'sleep': sleep_summary,
                'heart_rate': heart_rate_summary
            },
            'raw_data': health_data,
            'last_updated': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------- BACKGROUND SERVICES ----------

def start_background_services():
    def ble_worker():
        print("Starting BLE scanner...")
        while True:
            try:
                ble_scanner.is_scanning
                time.sleep(10)
                ble_scanner.stop_continuous_scan()
                time.sleep(5)
            except Exception as e:
                print(f"BLE Scanner error: {e}")
                time.sleep(10)

    def collector_worker():
        print("Starting data collector...")
        while True:
            try:
                data_collector.collect_ble_data(raw_data={})
                time.sleep(60)
            except Exception as e:
                print(f"Data Collector error: {e}")
                time.sleep(30)

    ble_thread = threading.Thread(target=ble_worker, daemon=True)
    collector_thread = threading.Thread(target=collector_worker, daemon=True)

    ble_thread.start()
    collector_thread.start()

    background_threads.extend([ble_thread, collector_thread])
    print("Background services started successfully")


@app.before_request
def initialize_app():
    if not background_threads:
        start_background_services()


@app.teardown_appcontext
def cleanup(error):
    if error:
        print(f"Request error: {error}")

# @app.route('/')
# def serve_index():
#     return send_from_directory(app.static_folder, 'index.html')

# @app.route('/<path:path>')
# def serve_static_file(path):
#     return send_from_directory(app.static_folder, path)

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
    print(f"Debug mode: {debug_mode}")

    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)
