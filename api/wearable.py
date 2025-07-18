from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import json
import sys
import os
import sqlite3

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import DatabaseManager
from ble.ble import BLEHealthMonitor
from collector.collector import HealthDataCollector

wearable_bp = Blueprint('wearable', __name__)
db = DatabaseManager()

def require_auth():
    """Check if user is authenticated"""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    return None

@wearable_bp.route('/devices', methods=['GET'])
def get_devices():
    """Get available BLE devices"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        # Initialize BLE scanner
        ble_scanner = BLEHealthMonitor()
        
        # Get available devices
        devices = ble_scanner.get_connected_devices()
        
        return jsonify({
            'devices': devices,
            'count': len(devices),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get devices: {str(e)}'}), 500

@wearable_bp.route('/connect', methods=['POST'])
def connect_device():
    """Connect to a BLE device"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        if not data or 'device_address' not in data:
            return jsonify({'error': 'Device address required'}), 400
        
        device_address = data['device_address']
        device_name = data.get('device_name', 'Unknown Device')
        device_type = data.get('device_type', 'fitness_tracker')
        
        user_id = session['user_id']
        
        # Initialize BLE scanner
        ble_scanner = BLEHealthMonitor()
        
        # Connect to device
        success = ble_scanner.connect_to_device(device_address)
        
        if success:
            # Store device connection in database
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO device_connections 
                    (user_id, device_name, device_type, mac_address, is_active, last_sync)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, device_name, device_type, device_address, 1, datetime.now()))
                conn.commit()
            
            return jsonify({
                'message': 'Device connected successfully',
                'device_address': device_address,
                'device_name': device_name,
                'connected': True
            }), 200
        else:
            return jsonify({
                'error': 'Failed to connect to device',
                'device_address': device_address,
                'connected': False
            }), 400
            
    except Exception as e:
        return jsonify({'error': f'Connection failed: {str(e)}'}), 500

@wearable_bp.route('/disconnect', methods=['POST'])
def disconnect_device():
    """Disconnect from a BLE device"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        if not data or 'device_address' not in data:
            return jsonify({'error': 'Device address required'}), 400
        
        device_address = data['device_address']
        user_id = session['user_id']
        
        # Initialize BLE scanner
        ble_scanner = BLEHealthMonitor()
        
        # Disconnect from device
        success = ble_scanner.disconnect_device(device_address)
        
        if success:
            # Update device connection status
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE device_connections 
                    SET is_active = 0, last_sync = ?
                    WHERE user_id = ? AND mac_address = ?
                ''', (datetime.now(), user_id, device_address))
                conn.commit()
            
            return jsonify({
                'message': 'Device disconnected successfully',
                'device_address': device_address,
                'connected': False
            }), 200
        else:
            return jsonify({
                'error': 'Failed to disconnect from device',
                'device_address': device_address
            }), 400
            
    except Exception as e:
        return jsonify({'error': f'Disconnection failed: {str(e)}'}), 500

@wearable_bp.route('/sync', methods=['POST'])
def sync_data():
    """Manually sync data from connected devices"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = session['user_id']
        
        # Initialize data collector
        data_collector = HealthDataCollector(db)
        
        # Collect data from all connected devices

        result = data_collector.collect_ble_data(user_id)
        if result == None:
            return jsonify({'error': 'No devices connected'}), 400
        
        return jsonify({
            'message': 'Data sync completed',
            'records_collected': result.get('records_collected', 0),
            'devices_synced': result.get('devices_synced', 0),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sync failed: {str(e)}'}), 500

@wearable_bp.route('/data/heart-rate', methods=['POST'])
def receive_heart_rate():
    """Receive heart rate data from wearable device"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        if not data or 'heart_rate' not in data:
            return jsonify({'error': 'Heart rate data required'}), 400
        
        user_id = session['user_id']
        heart_rate = data['heart_rate']
        device_id = data.get('device_id')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        # Validate heart rate
        if not isinstance(heart_rate, (int, float)) or heart_rate <= 0 or heart_rate > 300:
            return jsonify({'error': 'Invalid heart rate value'}), 400
        
        # Store heart rate data
        db.store_heart_rate(user_id, timestamp, heart_rate, device_id)
        
        return jsonify({
            'message': 'Heart rate data stored successfully',
            'heart_rate': heart_rate,
            'timestamp': timestamp
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to store heart rate: {str(e)}'}), 500

@wearable_bp.route('/data/activity', methods=['POST'])
def receive_activity():
    """Receive activity data from wearable device"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Activity data required'}), 400
        
        user_id = session['user_id']
        activity_date = data.get('date', datetime.now().date())
        
        # Extract activity metrics
        activity_data = {
            'total_steps': data.get('steps', 0),
            'total_distance': data.get('distance', 0.0),
            'very_active_minutes': data.get('very_active_minutes', 0),
            'fairly_active_minutes': data.get('fairly_active_minutes', 0),
            'lightly_active_minutes': data.get('lightly_active_minutes', 0),
            'sedentary_minutes': data.get('sedentary_minutes', 0),
            'calories': data.get('calories', 0)
        }
        
        # Store activity data
        db.store_daily_activity(user_id, activity_date, **activity_data)
        
        return jsonify({
            'message': 'Activity data stored successfully',
            'date': str(activity_date),
            'data': activity_data
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to store activity: {str(e)}'}), 500

@wearable_bp.route('/data/sleep', methods=['POST'])
def receive_sleep():
    """Receive sleep data from wearable device"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Sleep data required'}), 400
        
        user_id = session['user_id']
        sleep_date = data.get('date', datetime.now().date())
        
        # Extract sleep metrics
        sleep_data = {
            'total_sleep_records': data.get('sleep_records', 1),
            'total_minutes_asleep': data.get('minutes_asleep', 0),
            'total_time_in_bed': data.get('time_in_bed', 0),
            'sleep_efficiency': data.get('sleep_efficiency', 0.0)
        }
        
        # Store sleep data
        db.store_sleep_data(user_id, sleep_date, **sleep_data)
        
        return jsonify({
            'message': 'Sleep data stored successfully',
            'date': str(sleep_date),
            'data': sleep_data
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to store sleep: {str(e)}'}), 500

@wearable_bp.route('/status', methods=['GET'])
def get_wearable_status():
    """Get status of connected wearable devices"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = session['user_id']
        
        # Get connected devices from database
        with db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM device_connections 
                WHERE user_id = ? AND is_active = 1
                ORDER BY last_sync DESC
            ''', (user_id,))
            devices = [dict(row) for row in cursor.fetchall()]
        
        # Get recent data summary
        health_data = db.get_user_health_data(user_id, days=1)
        
        recent_data = {
            'heart_rate_readings': len(health_data['heart_rate']),
            'activity_days': len(health_data['activity']),
            'sleep_days': len(health_data['sleep']),
            'last_heart_rate': health_data['heart_rate'][0] if health_data['heart_rate'] else None,
            'last_activity': health_data['activity'][0] if health_data['activity'] else None,
            'last_sleep': health_data['sleep'][0] if health_data['sleep'] else None
        }
        
        return jsonify({
            'connected_devices': devices,
            'device_count': len(devices),
            'recent_data': recent_data,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500

@wearable_bp.route('/data/export', methods=['GET'])
def export_data():
    """Export user's health data"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = session['user_id']
        days = request.args.get('days', 30, type=int)
        
        # Get health data
        health_data = db.get_user_health_data(user_id, days=days)
        
        # Format for export
        export_data = {
            'user_id': user_id,
            'export_date': datetime.now().isoformat(),
            'data_range_days': days,
            'heart_rate_data': health_data['heart_rate'],
            'activity_data': health_data['activity'],
            'sleep_data': health_data['sleep']
        }
        
        return jsonify(export_data), 200
        
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500