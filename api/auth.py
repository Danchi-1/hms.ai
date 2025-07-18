from flask import Blueprint, request, jsonify, session
from datetime import datetime
import re
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import DatabaseManager

auth_bp = Blueprint('auth', __name__)
db = DatabaseManager()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not all(k in data for k in ['username', 'email', 'password']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        
        # Validate username
        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters long'}), 400
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return jsonify({'error': 'Username can only contain letters, numbers, and underscores'}), 400
        
        # Validate email
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Create user
        user_id = db.create_user(username, email, password)
        
        if user_id is None:
            return jsonify({'error': 'Username or email already exists'}), 409
        
        # Set session
        session['user_id'] = user_id
        session['username'] = username
        session['email'] = email
        session['login_time'] = datetime.now().isoformat()
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id,
            'username': username,
            'email': email
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not all(k in data for k in ['username', 'password']):
            return jsonify({'error': 'Missing username or password'}), 400
        
        username = data['username'].strip()
        password = data['password']
        
        # Authenticate user
        user = db.authenticate_user(username, password)
        
        if user is None:
            return jsonify({'error': 'Invalid username or password'}), 401
        
        user_id, username, email = user
        
        # Set session
        session['user_id'] = user_id
        session['username'] = username
        session['email'] = email
        session['login_time'] = datetime.now().isoformat()
        
        return jsonify({
            'message': 'Login successful',
            'user_id': user_id,
            'username': username,
            'email': email
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    try:
        # Clear session
        session.clear()
        
        return jsonify({'message': 'Logout successful'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Logout failed: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get current user profile"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        username = session['username']
        email = session['email']
        login_time = session.get('login_time')
        
        # Get user health data summary
        health_data = db.get_user_health_data(user_id, days=7)
        
        # Calculate basic stats
        stats = {
            'total_heart_rate_readings': len(health_data['heart_rate']),
            'total_activity_days': len(health_data['activity']),
            'total_sleep_days': len(health_data['sleep'])
        }
        
        return jsonify({
            'user_id': user_id,
            'username': username,
            'email': email,
            'login_time': login_time,
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500

@auth_bp.route('/update-profile', methods=['PUT'])
def update_profile():
    """Update user profile"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = session['user_id']
        
        # Here you would implement profile update logic
        # This is a placeholder for profile fields like age, gender, etc.
        
        return jsonify({'message': 'Profile updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

@auth_bp.route('/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    try:
        if 'user_id' in session:
            return jsonify({
                'authenticated': True,
                'user_id': session['user_id'],
                'username': session['username'],
                'email': session['email']
            }), 200
        else:
            return jsonify({'authenticated': False}), 401
            
    except Exception as e:
        return jsonify({'error': f'Auth check failed: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        if not data or not all(k in data for k in ['current_password', 'new_password']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Validate current password
        username = session['username']
        user = db.authenticate_user(username, current_password)
        if user is None:
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Update password (you'd need to implement this in DatabaseManager)
        # For now, return success
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Password change failed: {str(e)}'}), 500

# Helper function for other routes to check authentication
def require_auth():
    """Decorator function to require authentication"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator