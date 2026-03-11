from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, set_access_cookies, unset_jwt_cookies,
    jwt_required, get_jwt_identity, verify_jwt_in_request
)
from datetime import datetime
import re
import json
import sys
import os
from functools import wraps

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import db_manager as db, limiter

auth_bp = Blueprint('auth', __name__)

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
@limiter.limit("5 per minute")
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
        
        # Set JWT cookies
        response = jsonify({
            'message': 'User registered successfully',
            'user_id': user_id,
            'username': username,
            'email': email
        })
        access_token = create_access_token(identity=json.dumps({'id': user_id, 'username': username, 'email': email}))
        set_access_cookies(response, access_token)
        
        return response, 201
        
    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Missing request body'}), 400
            
        username_or_email = data.get('username') or data.get('email')
        password = data.get('password')

        if not username_or_email or not password:
             return jsonify({'error': 'Missing credentials'}), 400

        user = db.authenticate_user(username_or_email, password)
        
        if user is None:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        user_id, username, email = user
        
        # Set JWT cookies
        response = jsonify({
            'message': 'Login successful',
            'user_id': user_id,
            'username': username,
            'email': email
        })
        access_token = create_access_token(identity=json.dumps({'id': user_id, 'username': username, 'email': email}))
        set_access_cookies(response, access_token)
        
        return response, 200
        
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    try:
        response = jsonify({'message': 'Logout successful'})
        unset_jwt_cookies(response)
        return response, 200
    except Exception as e:
        return jsonify({'error': f'Logout failed: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    try:
        identity = json.loads(get_jwt_identity())
        user_id = identity['id']
        username = identity['username']
        email = identity['email']
        
        health_data = db.get_user_health_data(user_id, days=7)
        
        stats = {
            'total_heart_rate_readings': len(health_data['heart_rate']),
            'total_activity_days': len(health_data['activity']),
            'total_sleep_days': len(health_data['sleep'])
        }
        
        return jsonify({
            'user_id': user_id,
            'username': username,
            'email': email,
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500

@auth_bp.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        identity = json.loads(get_jwt_identity())
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = identity['id']
        # Placeholder for real update logic
        return jsonify({'message': 'Profile updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

@auth_bp.route('/check-auth', methods=['GET'])
@jwt_required(optional=True)
def check_auth():
    """Check if user is authenticated"""
    try:
        raw_identity = get_jwt_identity()
        identity = json.loads(raw_identity) if raw_identity else None
        if identity:
            return jsonify({
                'authenticated': True,
                'user_id': identity['id'],
                'username': identity['username'],
                'email': identity.get('email')
            }), 200
        else:
            return jsonify({'authenticated': False}), 401
            
    except Exception as e:
        return jsonify({'error': f'Auth check failed: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        identity = json.loads(get_jwt_identity())
        data = request.get_json()
        if not data or not all(k in data for k in ['current_password', 'new_password']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        username = identity['username']
        user = db.authenticate_user(username, current_password)
        if user is None:
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Password change failed: {str(e)}'}), 500

# Helper function for other routes to check authentication
def require_auth(func):
    """Decorator function to require authentication"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return func(*args, **kwargs)
        except Exception:
            return jsonify({'error': 'Authentication required'}), 401
    return wrapper