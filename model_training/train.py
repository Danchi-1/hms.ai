import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.model_selection import cross_val_score, GridSearchCV
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import inspect
import warnings
warnings.filterwarnings('ignore')

class HealthAITrainer:
    def __init__(self, processed_data_path='data/processed/', model_save_path='model_training/'):
        self.processed_data_path = processed_data_path
        self.model_save_path = model_save_path
        self.models = {}
        self.best_model = None
        self.best_model_name = None
        
        # Ensure model directory exists
        os.makedirs(model_save_path, exist_ok=True)
        
    def load_processed_data(self):
        """Load preprocessed training data"""
        try:
            # Load training data
            training_data = joblib.load(os.path.join(self.processed_data_path, 'training_data.pkl'))
            self.scaler = joblib.load(os.path.join(self.processed_data_path, 'scaler.pkl'))
            self.label_encoder = joblib.load(os.path.join(self.processed_data_path, 'label_encoder.pkl'))
            
            self.X_train = training_data['X_train']
            self.X_test = training_data['X_test']
            self.y_train = training_data['y_train']
            self.y_test = training_data['y_test']
            self.feature_names = training_data['feature_names']
            self.label_names = training_data['label_names']
            
            print(f" Loaded training data:")
            print(f"   - Training samples: {len(self.X_train)}")
            print(f"   - Test samples: {len(self.X_test)}")
            print(f"   - Features: {len(self.feature_names)}")
            print(f"   - Classes: {self.label_names}")
            
            return True
            
        except Exception as e:
            print(f" Error loading processed data: {e}")
            return False
    
    def initialize_models(self):
        """Initialize different ML models for comparison"""
        self.models = {
            'RandomForest': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            ),
            'GradientBoosting': GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            ),
            'LogisticRegression': LogisticRegression(
                random_state=42,
                max_iter=1000,
                multi_class='ovr'
            ),
            'SVM': SVC(
                kernel='rbf',
                random_state=42,
                probability=True  # Enable probability predictions
            )
        }
        
        print(f" Initialized {len(self.models)} models for training")
    
    def train_models(self):
        """Train all models and evaluate performance"""
        results = {}
        
        print("\n Training models...")
        
        for name, model in self.models.items():
            print(f"\n Training {name}...")
            
            # Train model
            model.fit(self.X_train, self.y_train)
            
            # Make predictions
            y_pred = model.predict(self.X_test)
            y_pred_proba = model.predict_proba(self.X_test) if hasattr(model, 'predict_proba') else None
            
            # Calculate metrics
            accuracy = accuracy_score(self.y_test, y_pred)
            
            # Cross-validation score
            cv_scores = cross_val_score(model, self.X_train, self.y_train, cv=5)
            
            results[name] = {
                'model': model,
                'accuracy': accuracy,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'predictions': y_pred,
                'probabilities': y_pred_proba
            }
            
            print(f"   - Accuracy: {accuracy:.4f}")
            print(f"   - CV Score: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
        
        self.results = results
        return results
    
    def evaluate_models(self):
        """Detailed evaluation of all models"""
        print("\n Model Evaluation Results:")
        print("=" * 50)
        
        best_accuracy = 0
        
        for name, result in self.results.items():
            print(f"\n{name}:")
            print(f"  Accuracy: {result['accuracy']:.4f}")
            print(f"  CV Score: {result['cv_mean']:.4f} (+/- {result['cv_std'] * 2:.4f})")
            
            # Classification report
            print(f"\n  Classification Report:")
            report = classification_report(self.y_test, result['predictions'], 
                                         target_names=self.label_names)
            print(report)
            
            # Track best model
            if result['accuracy'] > best_accuracy:
                best_accuracy = result['accuracy']
                self.best_model = result['model']
                self.best_model_name = name
        
        print(f"\n Best Model: {self.best_model_name} (Accuracy: {best_accuracy:.4f})")
        
        return self.best_model_name, best_accuracy
    
    def optimize_best_model(self):
        """Hyperparameter tuning for the best model"""
        print(f"\n⚡ Optimizing {self.best_model_name}...")
        
        param_grids = {
            'RandomForest': {
                'n_estimators': [50, 100, 200],
                'max_depth': [5, 10, 15, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            },
            'GradientBoosting': {
                'n_estimators': [50, 100, 200],
                'learning_rate': [0.01, 0.1, 0.2],
                'max_depth': [3, 5, 7],
                'subsample': [0.8, 0.9, 1.0]
            },
            'LogisticRegression': {
                'C': [0.1, 1, 10, 100],
                'penalty': ['l1', 'l2'],
                'solver': ['liblinear', 'lbfgs']
            },
            'SVM': {
                'C': [0.1, 1, 10],
                'kernel': ['rbf', 'linear'],
                'gamma': ['scale', 'auto']
            }
        }
        
        if self.best_model_name in param_grids:
            param_grid = param_grids[self.best_model_name]
            if self.best_model is None:
                print("No best model found. Please train models first.")
                return None
            # Create new model instance
            model_class = type(self.best_model)
            model_init = inspect.signature(model_class.__init__)
            if 'random_state' in model_init.parameters:
                base_model = model_class(random_state=42)
            else:
                base_model = model_class()
            
            # Grid search
            grid_search = GridSearchCV(
                base_model, 
                param_grid, 
                cv=5, 
                scoring='accuracy', 
                n_jobs=-1,
                verbose=1
            )
            
            grid_search.fit(self.X_train, self.y_train)
            
            # Update best model
            self.best_model = grid_search.best_estimator_
            
            print(f"Optimization complete!")
            print(f"Best parameters: {grid_search.best_params_}")
            print(f"Best CV score: {grid_search.best_score_:.4f}")
            
            # Test optimized model
            optimized_accuracy = accuracy_score(self.y_test, self.best_model.predict(self.X_test))
            print(f"   Optimized test accuracy: {optimized_accuracy:.4f}")
            
            return grid_search.best_params_
        else:
            print(f"No optimization parameters defined for {self.best_model_name}")
            return None
    
    def analyze_feature_importance(self):
        if self.best_model is not None and hasattr(self.best_model, 'feature_importances_'):
            importance = self.best_model.feature_importances_
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': importance
            }).sort_values('importance', ascending=False)
            print(f"\n Feature Importance ({self.best_model_name}):")
            print(importance_df.head(10))
            importance_df.to_csv(os.path.join(self.model_save_path, 'feature_importance.csv'), index=False)
            return importance_df
        else:
            print(f"Feature importance not available for {self.best_model_name}")
            return None
    
    def save_model(self):
        """Save the best trained model and associated files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save best model
        model_filename = f'best_model_{self.best_model_name}_{timestamp}.pkl'
        joblib.dump(self.best_model, os.path.join(self.model_save_path, model_filename))
        
        # Save as main model (for easy loading)
        joblib.dump(self.best_model, os.path.join(self.model_save_path, 'model.pkl'))

        if self.best_model is not None and hasattr(self.best_model, 'predict'):
            accuracy = accuracy_score(self.y_test, self.best_model.predict(self.X_test))
        else:
            accuracy = None
        
        # Save model metadata
        metadata = {
            'model_name': self.best_model_name,
            'timestamp': timestamp,
            'feature_names': self.feature_names,
            'label_names': self.label_names,
            'accuracy': accuracy,
            'model_file': model_filename
        }
        
        joblib.dump(metadata, os.path.join(self.model_save_path, 'model.pkl'))
        
        print(f"  Model saved successfully!")
        print(f"   - Model file: {model_filename}")
        print(f"   - Accuracy: {metadata['accuracy']:.4f}")
        
        return model_filename
    
    def create_health_predictor(self, user_data):
        """Create a health prediction function"""
        def predict_health_risk(heart_rate=None, steps=None, sleep_duration=None, 
                              active_minutes=None, sedentary_minutes=None, calories=None,
                              sleep_efficiency=None):
            """
            Predict health risk based on user health metrics
            
            Args:
                heart_rate: Average heart rate
                steps: Daily steps
                sleep_duration: Sleep duration in minutes
                active_minutes: Active minutes per day
                sedentary_minutes: Sedentary minutes per day
                calories: Daily calories burned
                sleep_efficiency: Sleep efficiency percentage
            
            Returns:
                dict: Prediction results with risk level and confidence
            """
            
            if not hasattr(self, 'best_model') or self.best_model is None:
                raise ValueError("Model not loaded.")
            if not hasattr(self, 'scaler') or self.scaler is None:
                raise ValueError("Scaler not loaded.")
            if not hasattr(self, 'feature_names') or self.feature_names is None:
                raise ValueError("Feature names not loaded.")
            X = [[user_data.get(f, 0) for f in self.feature_names]]
            X_scaled = self.scaler.transform(X)
            pred = self.best_model.predict(X_scaled)
            if hasattr(self.best_model, "predict_proba"):
                proba = self.best_model.predict_proba(X_scaled).max()
            else:
                proba = None

            if self.label_encoder is None:
                raise ValueError("Label encoder not loaded.")
            label = self.label_encoder.inverse_transform(pred)[0] if self.label_encoder is not None else str(pred[0])

            # Create feature vector (match training features)
            features = np.zeros(len(self.feature_names))
            
            # Map input parameters to features
            feature_mapping = {
                'avg_heart_rate': heart_rate,
                'avg_steps': steps,
                'avg_sleep_duration': sleep_duration,
                'avg_active_minutes': active_minutes,
                'avg_sedentary_minutes': sedentary_minutes,
                'avg_calories': calories,
                'avg_sleep_efficiency': sleep_efficiency
            }
            
            # Fill feature vector
            for i, feature_name in enumerate(self.feature_names):
                if feature_name in feature_mapping and feature_mapping[feature_name] is not None:
                    features[i] = feature_mapping[feature_name]
            
            # Scale features
            features_scaled = self.scaler.transform([features])

            if self.best_model is not None and hasattr(self.best_model, 'predict'):
                prediction = self.best_model.predict(features_scaled)[0]
            else:
                raise ValueError("No trained model available for prediction.")
            
            # Make prediction
            prediction = self.best_model.predict(features_scaled)[0]
            probabilities = self.best_model.predict_proba(features_scaled)[0]
            
            # Get risk level
            risk_level = self.label_encoder.inverse_transform([prediction])[0]
            confidence = max(probabilities)
            
            # Generate recommendations
            recommendations = self.generate_recommendations(risk_level, feature_mapping)
            
            return {
                'risk_level': risk_level,
                'confidence': confidence,
                'probabilities': dict(zip(self.label_names, probabilities)),
                'recommendations': recommendations
            }
        
        return predict_health_risk
    
    def generate_recommendations(self, risk_level, user_data):
        """Generate health recommendations based on risk level and user data"""
        recommendations = []
        
        if risk_level == 'High Risk':
            recommendations.append(" Consider consulting with a healthcare professional immediately.")
            recommendations.append(" Monitor your health metrics more closely.")
            
        if user_data.get('avg_steps', 0) < 5000:
            recommendations.append(" Try to increase daily steps to at least 8,000-10,000.")
            recommendations.append(" Consider adding 30 minutes of moderate exercise daily.")
            
        if user_data.get('avg_sleep_duration', 0) < 360:  # Less than 6 hours
            recommendations.append(" Aim for 7-9 hours of sleep per night.")
            recommendations.append(" Establish a consistent sleep schedule.")
            
        if user_data.get('avg_sedentary_minutes', 0) > 600:  # More than 10 hours
            recommendations.append(" Take regular breaks from sitting every hour.")
            recommendations.append(" Incorporate more movement throughout your day.")
            
        if user_data.get('avg_heart_rate', 0) > 100:
            recommendations.append(" Your resting heart rate seems elevated. Consider stress management.")
            recommendations.append(" Try relaxation techniques like deep breathing or meditation.")
            
        if risk_level == 'Low Risk':
            recommendations.append(" Great job! Keep maintaining your healthy lifestyle.")
            recommendations.append(" Continue monitoring your health metrics regularly.")
            
        return recommendations
    
    def train_complete_pipeline(self):
        """Complete training pipeline"""
        print(" Starting Health AI Model Training Pipeline")
        print("=" * 50)
        
        # Load data
        if not self.load_processed_data():
            return False
        
        # Initialize and train models
        self.initialize_models()
        self.train_models()
        
        # Evaluate and select best model
        self.evaluate_models()
        
        # Optimize best model
        self.optimize_best_model()
        
        # Analyze feature importance
        self.analyze_feature_importance()
        
        # Save model
        model_file = self.save_model()
        
        print("\n Training Complete!")
        print(f" Best model: {self.best_model_name}")
        print(f" Model saved: {model_file}")
        print(f" Ready for integration with Flask backend!")
        
        return True
    
    def load_model(self, model_path):
        """Load a trained model and related objects from disk"""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        self.best_model = joblib.load(model_path)
        scaler_path = os.path.join(os.path.dirname(model_path), "scaler.pkl")
        label_encoder_path = os.path.join(os.path.dirname(model_path), "label_encoder.pkl")
        features_path = os.path.join(os.path.dirname(model_path), "features.pkl")
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
        else:
            self.scaler = None
        if os.path.exists(label_encoder_path):
            self.label_encoder = joblib.load(label_encoder_path)
        else:
            self.label_encoder = None
        if os.path.exists(features_path):
            self.feature_names = joblib.load(features_path)
        else:
            self.feature_names = None
        # Optionally load model performance
        self.model_performance = None

    def predict_health_risk(self, user_data):
        """Predict health risk from user data dict"""
        # Ensure model and scaler are loaded
        if not hasattr(self, 'best_model') or self.best_model is None:
            raise ValueError("Model not loaded.")
        if not hasattr(self, 'scaler') or self.scaler is None:
            raise ValueError("Scaler not loaded.")
        if not hasattr(self, 'feature_names') or self.feature_names is None:
            raise ValueError("Feature names not loaded.")
        # Prepare feature vector
        X = [[user_data.get(f, 0) for f in self.feature_names]]
        X_scaled = self.scaler.transform(X)
        pred = self.best_model.predict(X_scaled)
        if hasattr(self.best_model, "predict_proba"):
            proba = self.best_model.predict_proba(X_scaled).max()
        else:
            proba = None
        label = self.label_encoder.inverse_transform(pred)[0] if self.label_encoder else str(pred[0])
        return {
            "risk_level": label,
            "confidence": float(proba) if proba is not None else None
        }

    def generate_health_recommendations(self, user_data, prediction_result):
        """Generate recommendations based on user data and prediction"""
        recs = []
        # Example: Steps
        steps = user_data.get('TotalSteps', 0)
        if steps < 5000:
            recs.append("Increase your daily steps to at least 8,000 for better health.")
        # Example: Sedentary
        sedentary = user_data.get('SedentaryMinutes', 0)
        if sedentary > 600:
            recs.append("Reduce sedentary time. Take breaks and move regularly.")
        # Example: Calories
        calories = user_data.get('Calories', 0)
        if calories < 1500:
            recs.append("Ensure adequate calorie intake for your activity level.")
        # Add more rules as needed
        return recs

    # Optionally, add a property for model_performance if you want to return metrics
    @property
    def model_performance(self):
        # Return a dict or string with model metrics if available
        return getattr(self, '_model_performance', None)

    @model_performance.setter
    def model_performance(self, value):
        self._model_performance = value

if __name__ == "__main__":
    # Initialize trainer
    trainer = HealthAITrainer()
    
    # Run complete training pipeline
    success = trainer.train_complete_pipeline()
    
    if success:
        print("\n Testing prediction function...")
        # Create predictor function
        predictor = trainer.create_health_predictor({})
        
        # Test prediction
        test_result = predictor(
            heart_rate=75,
            steps=8000,
            sleep_duration=420,  # 7 hours
            active_minutes=30,
            sedentary_minutes=480,  # 8 hours
            calories=2000,
            sleep_efficiency=85
        )
        
        print(f"\n Test Prediction Result:")
        print(f"   Risk Level: {test_result['risk_level']}")
        print(f"   Confidence: {test_result['confidence']:.2f}")
        print(f"   Recommendations: {len(test_result['recommendations'])} items")
        
        print("\n Model is ready for deployment!")
    else:
        print("\n Training failed. Please check your data and try again.")