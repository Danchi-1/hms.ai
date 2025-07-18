# api/predict.py
from flask import Blueprint, request, jsonify, session
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
import os
import logging

# Import your model trainer class
import sys
sys.path.append('../model_training')
from model_training.train import HealthAITrainer

predict_bp = Blueprint('predict', __name__)

health_model = None

# api/predict.py - Corrected sections

# 1. Fix the load_health_model function
def load_health_model():
    """Load the trained health risk model"""
    global health_model
    try:
        model_path = "model_training/model.pkl"
        if os.path.exists(model_path):
            health_model = HealthAITrainer()
            health_model.load_model(model_path)
            logging.info("Health risk model loaded successfully")
            return True
        else:
            logging.error(f"Model file not found: {model_path}")
            return False
    except Exception as e:
        logging.error(f"Error loading health model: {str(e)}")
        return False

# 2. Fix the predict_health_risk route
@predict_bp.route('/predict/health-risk', methods=['POST'])
def predict_health_risk():
    """Predict health risk based on user data"""
    try:
        # Check if model is loaded
        if health_model is None:
            if not load_health_model():
                return jsonify({
                    'error': 'Health model not available',
                    'message': 'Please train the model first'
                }), 503
        
        # Double check after loading attempt
        if health_model is None:
            return jsonify({
                'error': 'Health model still not available',
                'message': 'Model loading failed'
            }), 503
        
        # Get user data from request
        user_data = request.json
        
        if not user_data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Please provide health data for prediction'
            }), 400
        
        # Validate required fields
        required_fields = ['TotalSteps', 'Calories', 'SedentaryMinutes']
        missing_fields = [field for field in required_fields if field not in user_data]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400
        
        # Make prediction using the corrected method
        prediction_result = health_model.predict_health_risk(user_data)
        
        # Generate recommendations
        recommendations = health_model.generate_health_recommendations(user_data, prediction_result)
        
        # Prepare response
        response = {
            'prediction': prediction_result,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat(),
            'user_data_received': user_data
        }
        
        # Store prediction in session (optional)
        if 'user_id' in session:
            # Here you could store the prediction in your database
            pass
        
        return jsonify(response), 200
        
    except Exception as e:
        logging.error(f"Error in health risk prediction: {str(e)}")
        return jsonify({
            'error': 'Prediction failed',
            'message': str(e)
        }), 500

# 3. Fix the batch prediction route
@predict_bp.route('/predict/batch', methods=['POST'])
def predict_batch():
    """Predict health risk for multiple users"""
    try:
        if health_model is None:
            if not load_health_model():
                return jsonify({
                    'error': 'Health model not available'
                }), 503
        
        # Double check after loading attempt
        if health_model is None:
            return jsonify({
                'error': 'Health model still not available'
            }), 503
        
        batch_data = request.json
        
        if not batch_data or 'users' not in batch_data:
            return jsonify({
                'error': 'Invalid batch data format',
                'expected_format': {'users': [{'TotalSteps': 5000, 'Calories': 2000, '...': '...'}]}
            }), 400
        
        results = []
        for i, user_data in enumerate(batch_data['users']):
            try:
                # Use the correct method name
                prediction = health_model.predict_health_risk(user_data)
                recommendations = health_model.generate_health_recommendations(user_data, prediction)
                
                results.append({
                    'user_index': i,
                    'prediction': prediction,
                    'recommendations': recommendations,
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'user_index': i,
                    'error': str(e),
                    'status': 'failed'
                })
        
        return jsonify({
            'results': results,
            'total_users': len(batch_data['users']),
            'successful_predictions': len([r for r in results if r['status'] == 'success']),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Batch prediction failed',
            'message': str(e)
        }), 500

# 4. Fix the get_model_info route
@predict_bp.route('/predict/model-info', methods=['GET'])
def get_model_info():
    """Get information about the loaded model"""
    try:
        if health_model is None:
            return jsonify({
                'model_loaded': False,
                'message': 'No model currently loaded'
            }), 200
        
        model_info = {
            'model_loaded': True,
            'feature_names': getattr(health_model, 'feature_names', None),
            'model_performance': getattr(health_model, 'model_performance', None),
            'supported_risk_levels': health_model.label_encoder.classes_.tolist() if hasattr(health_model, 'label_encoder') and health_model.label_encoder else None
        }
        
        return jsonify(model_info), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to get model info',
            'message': str(e)
        }), 500

# 5. Fix the incomplete calculate_health_score function
@predict_bp.route('/predict/health-score', methods=['POST'])
def calculate_health_score():
    """Calculate a simple health score based on key metrics"""
    try:
        user_data = request.json
        
        if not user_data:
            return jsonify({
                'error': 'No data provided'
            }), 400
        
        score = 0
        max_score = 100
        details = {}
        
        # Steps score (20 points)
        steps = user_data.get('TotalSteps', 0)
        if steps >= 10000:
            steps_score = 20
        elif steps >= 8000:
            steps_score = 16
        elif steps >= 5000:
            steps_score = 12
        else:
            steps_score = max(0, int(steps / 5000 * 12))
        
        score += steps_score
        details['steps'] = {'score': steps_score, 'max': 20, 'value': steps}
        
        # Sleep score (20 points)
        sleep_hours = user_data.get('SleepHours', 0)
        if 7 <= sleep_hours <= 9:
            sleep_score = 20
        elif 6 <= sleep_hours <= 10:
            sleep_score = 15
        elif sleep_hours > 0:
            sleep_score = max(0, int(20 - abs(sleep_hours - 7.5) * 3))
        else:
            sleep_score = 0
        
        score += sleep_score
        details['sleep'] = {'score': sleep_score, 'max': 20, 'value': sleep_hours}
        
        # Activity score (20 points)
        very_active = user_data.get('VeryActiveMinutes', 0)
        fairly_active = user_data.get('FairlyActiveMinutes', 0)
        total_active = very_active + fairly_active
        
        if total_active >= 30:
            activity_score = 20
        elif total_active >= 20:
            activity_score = 15
        elif total_active >= 10:
            activity_score = 10
        else:
            activity_score = max(0, int(total_active / 10 * 10))
        
        score += activity_score
        details['activity'] = {'score': activity_score, 'max': 20, 'value': total_active}
        
        # Heart rate score (20 points)
        hr_avg = user_data.get('hr_avg', 0)
        if hr_avg > 0:
            if 60 <= hr_avg <= 100:
                hr_score = 20
            elif 50 <= hr_avg <= 110:
                hr_score = 15
            else:
                hr_score = 10
        else:
            hr_score = 0
        
        score += hr_score
        details['heart_rate'] = {'score': hr_score, 'max': 20, 'value': hr_avg}
        
        # Sedentary score (20 points) - COMPLETED
        sedentary_minutes = user_data.get('SedentaryMinutes', 0)
        if sedentary_minutes <= 480:  # 8 hours
            sedentary_score = 20
        elif sedentary_minutes <= 600:  # 10 hours
            sedentary_score = 15
        elif sedentary_minutes <= 720:  # 12 hours
            sedentary_score = 10
        else:
            sedentary_score = 5
        
        score += sedentary_score
        details['sedentary'] = {'score': sedentary_score, 'max': 20, 'value': sedentary_minutes}
        
        # Calculate percentage
        percentage = (score / max_score) * 100
        
        # Determine health grade
        if percentage >= 90:
            grade = 'A'
            message = 'Excellent health metrics!'
        elif percentage >= 80:
            grade = 'B'
            message = 'Good health metrics with room for improvement'
        elif percentage >= 70:
            grade = 'C'
            message = 'Average health metrics, focus on improvements'
        elif percentage >= 60:
            grade = 'D'
            message = 'Below average health metrics, attention needed'
        else:
            grade = 'F'
            message = 'Poor health metrics, immediate action recommended'
        
        return jsonify({
            'health_score': score,
            'max_score': max_score,
            'percentage': round(percentage, 1),
            'grade': grade,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to calculate health score',
            'message': str(e)
        }), 500