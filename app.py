from model_training.preprocess import HealthDataPreprocessor
from database.models import DatabaseManager
from ble.ble import BLEHealthMonitor
from collector.collector import HealthDataCollector
from model_training.train import HealthAITrainer
from api.auth import auth_bp
from api.predict import predict_bp
from api.wearable import wearable_bp
from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
from api.auth import login, register
import os
import sys
import threading
import time
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    template_folder='frontend/templates',
    static_folder='frontend/static'
)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Enable CORS for frontend communication
CORS(app, supports_credentials=True)

# Initialize database
db = DatabaseManager()

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(predict_bp, url_prefix='/api/predict')
app.register_blueprint(wearable_bp, url_prefix='/api/wearable')



@app.route('/')
def index():
    """API status endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Health Monitoring System API',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/login')
def login_page():
    return render_template('index.html')  # Your login/signup page

@app.route('/dashboard')
def dashboard_page():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if login():
        session['user'] = username
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if register():
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Signup failed'})

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
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
    """Get dashboard data for user"""
    try:
        # Get user health data
        health_data = db.get_user_health_data(user_id, days=7)
        
        # Calculate summary statistics
        activity_summary = {}
        if health_data['activity']:
            recent_activity = health_data['activity'][:7]  # Last 7 days
            activity_summary = {
                'avg_steps': sum(a['total_steps'] for a in recent_activity) / len(recent_activity),
                'avg_calories': sum(a['calories'] for a in recent_activity) / len(recent_activity),
                'avg_active_minutes': sum(a['very_active_minutes'] + a['fairly_active_minutes'] 
                                         for a in recent_activity) / len(recent_activity)
            }
        
        sleep_summary = {}
        if health_data['sleep']:
            recent_sleep = health_data['sleep'][:7]  # Last 7 days
            sleep_summary = {
                'avg_sleep_duration': sum(s['total_minutes_asleep'] for s in recent_sleep) / len(recent_sleep),
                'avg_sleep_efficiency': sum(s['sleep_efficiency'] for s in recent_sleep) / len(recent_sleep)
            }
        
        heart_rate_summary = {}
        if health_data['heart_rate']:
            recent_hr = health_data['heart_rate'][-100:]  # Last 100 readings
            heart_rate_summary = {
                'avg_heart_rate': sum(h['heart_rate'] for h in recent_hr) / len(recent_hr),
                'max_heart_rate': max(h['heart_rate'] for h in recent_hr),
                'min_heart_rate': min(h['heart_rate'] for h in recent_hr)
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

def start_background_services():
    """Start background services for BLE scanning and data collection"""
    global data_collector, ble_scanner, background_threads
    
    try:
        # Start BLE scanning in background thread
        def ble_worker():
            print("Starting BLE scanner...")
            while True:
                try:
                    ble_scanner.is_scanning
                    time.sleep(10)  # Scan for 10 seconds
                    ble_scanner.stop_continuous_scan()
                    time.sleep(5)   # Rest for 5 seconds
                except Exception as e:
                    print(f"BLE Scanner error: {e}")
                    time.sleep(10)
        
        # Start data collection in background thread
        def collector_worker():
            print("Starting data collector...")
            while True:
                try:
                    data_collector. collect_ble_data(raw_data={})
                    time.sleep(60)  # Collect data every minute
                except Exception as e:
                    print(f"Data Collector error: {e}")
                    time.sleep(30)
        
        # Start background threads
        ble_thread = threading.Thread(target=ble_worker, daemon=True)
        collector_thread = threading.Thread(target=collector_worker, daemon=True)
        
        ble_thread.start()
        collector_thread.start()
        
        background_threads.extend([ble_thread, collector_thread])
        
        print("Background services started successfully")
        
    except Exception as e:
        print(f"Error starting background services: {e}")

@app.before_request
def initialize_app():
    """Initialize app on first request"""
    print("Initializing Health Monitoring System...")
    
    # Start background services
    start_background_services()
    
    print("Health Monitoring System initialized successfully!")

@app.teardown_appcontext
def cleanup(error):
    """Cleanup resources"""
    if error:
        print(f"Request error: {error}")

if __name__ == '__main__':
    # Check if model exists
    model_path = 'model_training/model.pkl'
    if not os.path.exists(model_path):
        print(" Warning: No trained model found. Please run training first:")
        print("   python model_training/preprocess.py")
        print("   python model_training/train.py")
    
    # Run Flask app
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    
    print(f"Health Monitoring System starting on port {port}")
    print(f"Debug mode: {debug_mode}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        threaded=True
    )