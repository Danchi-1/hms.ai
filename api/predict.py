from flask import Blueprint, request, jsonify, session
from pydantic import ValidationError
from api.schemas import PredictHealthScoreRequest
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
    """Calculate a hybrid health score based on heuristics and ML prediction"""
    try:
        # Check if model is loaded for ML inference
        if health_model is None:
            load_health_model()
        try:
            req_data = request.json or {}
            validated_data = PredictHealthScoreRequest.model_validate(req_data)
            # Pydantic dump returns dictionary correctly typed
            user_data = validated_data.model_dump()
        except ValidationError as e:
            return jsonify({
                'error': 'Invalid payload',
                'details': e.errors()
            }), 400
        
        # Calculate ML Inference
        score = 0
        max_score = 100
        details = {}
        ml_prediction = None
        percentage = 70.0
        
        # ML Inference Integration
        if health_model is not None:
            try:
                hr_avg = user_data.get('hr_avg', 0)
                steps = user_data.get('TotalSteps', 0)
                sleep_hours = user_data.get('SleepHours', 0)
                sedentary_minutes = user_data.get('SedentaryMinutes', 0)
                very_active = user_data.get('VeryActiveMinutes', 0)
                fairly_active = user_data.get('FairlyActiveMinutes', 0)
                total_active = very_active + fairly_active

                # Map frontend metrics to the model's expected feature names
                ml_data = {
                    'avg_heart_rate': hr_avg if hr_avg > 0 else 72,
                    'avg_steps': steps,
                    'avg_sleep_duration': sleep_hours * 60,
                    'avg_active_minutes': total_active,
                    'avg_sedentary_minutes': sedentary_minutes,
                    'avg_calories': user_data.get('Calories', 2000),
                    'avg_sleep_efficiency': 85 
                }
                
                ml_prediction = health_model.predict_health_risk(ml_data)
                risk_level = ml_prediction.get('risk_level', 'Unknown')
                confidence = ml_prediction.get('confidence', 0.5)

                # Map ML Risk Level to a percentage score (0-100)
                if 'Low' in risk_level:
                    percentage = 80 + (20 * confidence)
                elif 'Medium' in risk_level:
                    percentage = 60 + (20 * confidence)
                elif 'High' in risk_level:
                    percentage = max(0, 60 - (30 * confidence))
                else:
                    percentage = 70.0

                score = int((percentage / 100) * max_score)
                details['ml_inference'] = {'score': score, 'max': max_score, 'value': risk_level, 'confidence': confidence}

            except Exception as e:
                logging.error(f"ML inference fallback: {str(e)}")
        
        # Determine final health grade and message
        if percentage >= 90:
            grade = 'A'
            message = 'Excellent health metrics! Keep it up.'
        elif percentage >= 80:
            grade = 'B'
            message = 'Good health metrics with a little room for improvement.'
        elif percentage >= 70:
            grade = 'C'
            message = 'Average health metrics, focus on steady improvements.'
        elif percentage >= 60:
            grade = 'D'
            message = 'Below average health metrics, attention needed.'
        else:
            grade = 'F'
            message = 'Poor health metrics, immediate action recommended.'
            
        # Append ML warning if applicable
        if ml_prediction and 'High' in ml_prediction.get('risk_level', ''):
            message = "⚠️ " + message + " AI detected potential high risk factors."
        
        return jsonify({
            'health_score': score, # Keep base score for UI details
            'max_score': max_score,
            'percentage': round(percentage, 1),
            'grade': grade,
            'message': message,
            'details': details,
            'ml_insight': ml_prediction,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to calculate health score',
            'message': str(e)
        }), 500