import sqlite3
from datetime import datetime
import hashlib
import os

class DatabaseManager:
    def __init__(self, db_path='data/sqlite.db'):
        self.db_path = db_path
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    
    def init_database(self):
        """Initialize database with all required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # User profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    age INTEGER,
                    gender TEXT,
                    height REAL,
                    weight REAL,
                    activity_level TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Heart rate data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS heart_rate_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    heart_rate INTEGER NOT NULL,
                    device_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Daily activity table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    activity_date DATE NOT NULL,
                    total_steps INTEGER DEFAULT 0,
                    total_distance REAL DEFAULT 0.0,
                    very_active_minutes INTEGER DEFAULT 0,
                    fairly_active_minutes INTEGER DEFAULT 0,
                    lightly_active_minutes INTEGER DEFAULT 0,
                    sedentary_minutes INTEGER DEFAULT 0,
                    calories INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Sleep data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sleep_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    sleep_date DATE NOT NULL,
                    total_sleep_records INTEGER DEFAULT 1,
                    total_minutes_asleep INTEGER DEFAULT 0,
                    total_time_in_bed INTEGER DEFAULT 0,
                    sleep_efficiency REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Health predictions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    prediction_date TIMESTAMP NOT NULL,
                    health_score REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    recommendations TEXT,
                    confidence_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Device connections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    device_name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    mac_address TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    last_sync TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def create_user(self, username, email, password):
        """Create a new user"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash)
                    VALUES (?, ?, ?)
                ''', (username, email, password_hash))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None
    
    def authenticate_user(self, username, password):
        """Authenticate user login"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email FROM users 
                WHERE username = ? AND password_hash = ?
            ''', (username, password_hash))
            return cursor.fetchone()
    
    def store_heart_rate(self, user_id, timestamp, heart_rate, device_id=None):
        """Store heart rate data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO heart_rate_data (user_id, timestamp, heart_rate, device_id)
                VALUES (?, ?, ?, ?)
            ''', (user_id, timestamp, heart_rate, device_id))
            conn.commit()
    
    def store_daily_activity(self, user_id, activity_date, **kwargs):
        """Store daily activity data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO daily_activity 
                (user_id, activity_date, total_steps, total_distance, 
                 very_active_minutes, fairly_active_minutes, 
                 lightly_active_minutes, sedentary_minutes, calories)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, activity_date,
                kwargs.get('total_steps', 0),
                kwargs.get('total_distance', 0.0),
                kwargs.get('very_active_minutes', 0),
                kwargs.get('fairly_active_minutes', 0),
                kwargs.get('lightly_active_minutes', 0),
                kwargs.get('sedentary_minutes', 0),
                kwargs.get('calories', 0)
            ))
            conn.commit()
    
    def store_sleep_data(self, user_id, sleep_date, **kwargs):
        """Store sleep data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sleep_data 
                (user_id, sleep_date, total_sleep_records, total_minutes_asleep, 
                 total_time_in_bed, sleep_efficiency)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id, sleep_date,
                kwargs.get('total_sleep_records', 1),
                kwargs.get('total_minutes_asleep', 0),
                kwargs.get('total_time_in_bed', 0),
                kwargs.get('sleep_efficiency', 0.0)
            ))
            conn.commit()
    
    def get_user_health_data(self, user_id, days=30):
        """Get comprehensive health data for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get recent heart rate data
            cursor.execute('''
                SELECT * FROM heart_rate_data 
                WHERE user_id = ? AND timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp DESC
            '''.format(days), (user_id,))
            heart_rate_data = cursor.fetchall()
            
            # Get recent daily activity
            cursor.execute('''
                SELECT * FROM daily_activity 
                WHERE user_id = ? AND activity_date >= date('now', '-{} days')
                ORDER BY activity_date DESC
            '''.format(days), (user_id,))
            activity_data = cursor.fetchall()
            
            # Get recent sleep data
            cursor.execute('''
                SELECT * FROM sleep_data 
                WHERE user_id = ? AND sleep_date >= date('now', '-{} days')
                ORDER BY sleep_date DESC
            '''.format(days), (user_id,))
            sleep_data = cursor.fetchall()
            
            return {
                'heart_rate': [dict(row) for row in heart_rate_data],
                'activity': [dict(row) for row in activity_data],
                'sleep': [dict(row) for row in sleep_data]
            }
    
    def store_health_prediction(self, user_id, health_score, risk_level, recommendations, confidence_score):
        """Store AI health prediction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO health_predictions 
                (user_id, prediction_date, health_score, risk_level, 
                 recommendations, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, datetime.now(), health_score, risk_level, 
                  recommendations, confidence_score))
            conn.commit()

# Initialize database when module is imported
if __name__ == "__main__":
    db = DatabaseManager()
    print("Database initialized successfully!")