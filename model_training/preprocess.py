import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sqlite3
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib

class HealthDataPreprocessor:
    def __init__(self, raw_data_path='data/raw/', processed_data_path='data/processed/'):
        self.raw_data_path = raw_data_path
        self.processed_data_path = processed_data_path
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        
        # Ensure processed directory exists
        os.makedirs(processed_data_path, exist_ok=True)
    
    def load_fitbit_data(self):
        """Load all Fitbit CSV files"""
        try:
            # Load heart rate data (using seconds data for more granular analysis)
            heart_rate_data = None
            heart_rate_file = os.path.join(self.raw_data_path, 'heartrate_seconds_merged.csv')
            if os.path.exists(heart_rate_file):
                heart_rate_data = pd.read_csv(heart_rate_file)
                print(f"Loaded heart rate data: {len(heart_rate_data)} records")
            
            # Load daily activity data
            daily_activity = None
            activity_file = os.path.join(self.raw_data_path, 'dailyActivity_merged.csv')
            if os.path.exists(activity_file):
                daily_activity = pd.read_csv(activity_file)
                print(f"Loaded daily activity data: {len(daily_activity)} records")
            
            # Load sleep data
            sleep_data = None
            sleep_file = os.path.join(self.raw_data_path, 'minuteSleep_merged.csv')
            if os.path.exists(sleep_file):
                sleep_data = pd.read_csv(sleep_file)
                print(f"Loaded sleep data: {len(sleep_data)} records")
            
            # Load additional data for richer features
            additional_data = {}
            
            # Load hourly data for trends
            hourly_files = ['hourlyCalories_merged.csv', 'hourlyIntensities_merged.csv', 'hourlySteps_merged.csv']
            for file in hourly_files:
                file_path = os.path.join(self.raw_data_path, file)
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    key = file.replace('_merged.csv', '').replace('hourly', '').lower()
                    additional_data[key] = df
                    print(f"Loaded {key} data: {len(df)} records")
            
            # Load weight data if available
            weight_file = os.path.join(self.raw_data_path, 'weightLogInfo_merged.csv')
            if os.path.exists(weight_file):
                additional_data['weight'] = pd.read_csv(weight_file)
                print(f"Loaded weight data: {len(additional_data['weight'])} records")
            
            return {
                'heart_rate': heart_rate_data,
                'daily_activity': daily_activity,
                'sleep': sleep_data,
                'additional': additional_data
            }
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return None
    
    def clean_heart_rate_data(self, df):
        """Clean and validate heart rate data"""
        if df is None:
            return None
            
        # Convert timestamp column
        time_columns = ['Time', 'ActivityMinute', 'Date']
        for col in time_columns:
            if col in df.columns:
                df['timestamp'] = pd.to_datetime(df[col])
                break
        
        # Rename value column
        value_columns = ['Value', 'HeartRate', 'heart_rate']
        for col in value_columns:
            if col in df.columns:
                df['heart_rate'] = df[col]
                break
        
        # Clean data
        df = df.dropna(subset=['heart_rate'])
        df = df[(df['heart_rate'] >= 30) & (df['heart_rate'] <= 220)]  # Valid heart rate range
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['Id', 'timestamp'])
        
        return df[['Id', 'timestamp', 'heart_rate']]
    
    def clean_daily_activity_data(self, df):
        """Clean and validate daily activity data"""
        if df is None:
            return None
            
        # Convert date column
        date_columns = ['ActivityDate', 'Date', 'ActivityDay']
        for col in date_columns:
            if col in df.columns:
                df['activity_date'] = pd.to_datetime(df[col])
                break
        
        # Standardize column names
        column_mapping = {
            'TotalSteps': 'total_steps',
            'TotalDistance': 'total_distance',
            'VeryActiveMinutes': 'very_active_minutes',
            'FairlyActiveMinutes': 'fairly_active_minutes',
            'LightlyActiveMinutes': 'lightly_active_minutes',
            'SedentaryMinutes': 'sedentary_minutes',
            'Calories': 'calories'
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df[new_name] = df[old_name]
        
        # Clean data
        df = df.fillna(0)
        df = df[df['total_steps'] >= 0]  # Valid step counts
        df = df[df['calories'] > 0]      # Valid calorie burns
        
        return df[['Id', 'activity_date'] + list(column_mapping.values())]
    
    def clean_sleep_data(self, df):
        """Clean and validate sleep data"""
        if df is None:
            return None
            
        # The minuteSleep_merged.csv has different structure
        # Convert date column
        if 'date' in df.columns:
            df['sleep_date'] = pd.to_datetime(df['date']).dt.date
        
        # Group by user and date to get daily sleep summary
        sleep_summary = df.groupby(['Id', 'sleep_date']).agg({
            'value': ['count', 'sum'],  # count of sleep minutes, sum of sleep values
            'logId': 'first'  # keep track of log ID
        }).reset_index()
        
        # Flatten column names
        sleep_summary.columns = ['Id', 'sleep_date', 'total_sleep_records', 'total_minutes_asleep', 'log_id']
        
        # Calculate time in bed (approximate)
        sleep_summary['total_time_in_bed'] = sleep_summary['total_minutes_asleep'] * 1.1  # Add 10% buffer
        
        # Calculate sleep efficiency
        sleep_summary['sleep_efficiency'] = (sleep_summary['total_minutes_asleep'] / sleep_summary['total_time_in_bed']) * 100
        sleep_summary['sleep_efficiency'] = sleep_summary['sleep_efficiency'].fillna(0)
        
        # Clean data
        sleep_summary = sleep_summary[sleep_summary['total_minutes_asleep'] > 0]  # Valid sleep time
        
        return sleep_summary[['Id', 'sleep_date', 'total_sleep_records', 'total_minutes_asleep', 'total_time_in_bed', 'sleep_efficiency']]
    
    def create_health_features(self, heart_rate_df, activity_df, sleep_df):
        """Create features for ML model"""
        features_list = []
        
        # Get unique users
        user_ids = set()
        if heart_rate_df is not None:
            user_ids.update(heart_rate_df['Id'].unique())
        if activity_df is not None:
            user_ids.update(activity_df['Id'].unique())
        if sleep_df is not None:
            user_ids.update(sleep_df['Id'].unique())
        
        for user_id in user_ids:
            user_features = {'user_id': user_id}
            
            # Heart rate features
            if heart_rate_df is not None:
                user_hr = heart_rate_df[heart_rate_df['Id'] == user_id]
                if not user_hr.empty:
                    user_features.update({
                        'avg_heart_rate': user_hr['heart_rate'].mean(),
                        'max_heart_rate': user_hr['heart_rate'].max(),
                        'min_heart_rate': user_hr['heart_rate'].min(),
                        'hr_std': user_hr['heart_rate'].std(),
                        'hr_range': user_hr['heart_rate'].max() - user_hr['heart_rate'].min()
                    })
            
            # Activity features
            if activity_df is not None:
                user_activity = activity_df[activity_df['Id'] == user_id]
                if not user_activity.empty:
                    user_features.update({
                        'avg_steps': user_activity['total_steps'].mean(),
                        'avg_distance': user_activity['total_distance'].mean(),
                        'avg_calories': user_activity['calories'].mean(),
                        'avg_active_minutes': user_activity['very_active_minutes'].mean(),
                        'avg_sedentary_minutes': user_activity['sedentary_minutes'].mean()
                    })
            
            # Sleep features
            if sleep_df is not None:
                user_sleep = sleep_df[sleep_df['Id'] == user_id]
                if not user_sleep.empty:
                    user_features.update({
                        'avg_sleep_duration': user_sleep['total_minutes_asleep'].mean(),
                        'avg_sleep_efficiency': user_sleep['sleep_efficiency'].mean(),
                        'avg_time_in_bed': user_sleep['total_time_in_bed'].mean()
                    })
            
            features_list.append(user_features)
        
        return pd.DataFrame(features_list)
    
    def create_health_labels(self, features_df):
        """Create health risk labels based on features"""
        labels = []
        
        for _, row in features_df.iterrows():
            risk_factors = 0
            
            # Heart rate risk factors
            if 'avg_heart_rate' in row:
                if row['avg_heart_rate'] > 100 or row['avg_heart_rate'] < 50:
                    risk_factors += 1
            
            # Activity risk factors
            if 'avg_steps' in row:
                if row['avg_steps'] < 5000:  # Low activity
                    risk_factors += 1
            
            if 'avg_sedentary_minutes' in row:
                if row['avg_sedentary_minutes'] > 600:  # Too sedentary
                    risk_factors += 1
            
            # Sleep risk factors
            if 'avg_sleep_duration' in row:
                if row['avg_sleep_duration'] < 360 or row['avg_sleep_duration'] > 600:  # 6-10 hours
                    risk_factors += 1
            
            if 'avg_sleep_efficiency' in row:
                if row['avg_sleep_efficiency'] < 80:  # Poor sleep efficiency
                    risk_factors += 1
            
            # Assign risk level
            if risk_factors == 0:
                labels.append('Low Risk')
            elif risk_factors <= 2:
                labels.append('Medium Risk')
            else:
                labels.append('High Risk')
        
        return labels
    
    def preprocess_data(self):
        """Main preprocessing pipeline"""
        print("Loading raw data...")
        raw_data = self.load_fitbit_data()
        
        if raw_data is None:
            print("Failed to load data")
            return None
        
        print("Cleaning data...")
        # Clean individual datasets
        heart_rate_clean = self.clean_heart_rate_data(raw_data['heart_rate'])
        activity_clean = self.clean_daily_activity_data(raw_data['daily_activity'])
        sleep_clean = self.clean_sleep_data(raw_data['sleep'])
        
        print("Creating features...")
        # Create features for ML
        features_df = self.create_health_features(heart_rate_clean, activity_clean, sleep_clean)
        
        print("Creating labels...")
        # Create health risk labels
        labels = self.create_health_labels(features_df)
        features_df['health_risk'] = labels
        
        print("Preparing training data...")
        # Prepare for ML training
        feature_columns = [col for col in features_df.columns if col not in ['user_id', 'health_risk']]
        X = features_df[feature_columns].fillna(0)
        y = features_df['health_risk']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Encode labels
        y_train_encoded = self.label_encoder.fit_transform(y_train)
        y_test_encoded = self.label_encoder.transform(y_test)
        
        # Save processed data
        processed_data = {
            'X_train': X_train_scaled,
            'X_test': X_test_scaled,
            'y_train': y_train_encoded,
            'y_test': y_test_encoded,
            'feature_names': feature_columns,
            'label_names': self.label_encoder.classes_
        }
        
        # Save to files
        joblib.dump(processed_data, os.path.join(self.processed_data_path, 'training_data.pkl'))
        joblib.dump(self.scaler, os.path.join(self.processed_data_path, 'scaler.pkl'))
        joblib.dump(self.label_encoder, os.path.join(self.processed_data_path, 'label_encoder.pkl'))
        
        # Save clean datasets
        if heart_rate_clean is not None:
            heart_rate_clean.to_csv(os.path.join(self.processed_data_path, 'heart_rate_clean.csv'), index=False)
        if activity_clean is not None:
            activity_clean.to_csv(os.path.join(self.processed_data_path, 'daily_activity_clean.csv'), index=False)
        if sleep_clean is not None:
            sleep_clean.to_csv(os.path.join(self.processed_data_path, 'sleep_data_clean.csv'), index=False)
        
        features_df.to_csv(os.path.join(self.processed_data_path, 'features.csv'), index=False)
        
        print(f"Data preprocessing complete!")
        print(f"Training samples: {len(X_train)}")
        print(f"Test samples: {len(X_test)}")
        print(f"Features: {len(feature_columns)}")
        print(f"Classes: {list(self.label_encoder.classes_)}")
        
        return processed_data

if __name__ == "__main__":
    preprocessor = HealthDataPreprocessor()
    data = preprocessor.preprocess_data()