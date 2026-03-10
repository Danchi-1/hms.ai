from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    heart_rate_data = db.relationship('HeartRateData', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    daily_activity = db.relationship('DailyActivity', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sleep_data = db.relationship('SleepData', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    predictions = db.relationship('HealthPrediction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    devices = db.relationship('DeviceConnection', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    activity_level = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HeartRateData(db.Model):
    __tablename__ = 'heart_rate_data'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    heart_rate = db.Column(db.Integer, nullable=False)
    device_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DailyActivity(db.Model):
    __tablename__ = 'daily_activity'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_date = db.Column(db.Date, nullable=False, index=True)
    total_steps = db.Column(db.Integer, default=0)
    total_distance = db.Column(db.Float, default=0.0)
    very_active_minutes = db.Column(db.Integer, default=0)
    fairly_active_minutes = db.Column(db.Integer, default=0)
    lightly_active_minutes = db.Column(db.Integer, default=0)
    sedentary_minutes = db.Column(db.Integer, default=0)
    calories = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SleepData(db.Model):
    __tablename__ = 'sleep_data'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sleep_date = db.Column(db.Date, nullable=False, index=True)
    total_sleep_records = db.Column(db.Integer, default=1)
    total_minutes_asleep = db.Column(db.Integer, default=0)
    total_time_in_bed = db.Column(db.Integer, default=0)
    sleep_efficiency = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HealthPrediction(db.Model):
    __tablename__ = 'health_predictions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    prediction_date = db.Column(db.DateTime, nullable=False, index=True)
    health_score = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(50), nullable=False)
    recommendations = db.Column(db.Text)
    confidence_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DeviceConnection(db.Model):
    __tablename__ = 'device_connections'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    mac_address = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Legacy wrapper to bridge API calls while migrating (Temporary)
class DatabaseManager:
    def __init__(self, db_path='data/sqlite.db'):
        pass
        
    def get_connection(self):
        pass
        
    def init_database(self):
        db.create_all()

    def create_user(self, username, email, password):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user = User(username=username, email=email, password_hash=password_hash)
        try:
            db.session.add(user)
            db.session.commit()
            return user.id
        except Exception:
            db.session.rollback()
            return None

    def authenticate_user(self, username, password):
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user and user.check_password(password):
            return (user.id, user.username, user.email)
        return None

    def store_heart_rate(self, user_id, timestamp, heart_rate, device_id=None):
        hr_data = HeartRateData(user_id=user_id, timestamp=timestamp, heart_rate=heart_rate, device_id=device_id)
        db.session.add(hr_data)
        db.session.commit()

    def store_heart_rate_batch(self, batch_data):
        hr_objects = [HeartRateData(user_id=data[0], timestamp=data[1], heart_rate=data[2], device_id=data[3]) for data in batch_data]
        db.session.add_all(hr_objects)
        db.session.commit()

    def store_daily_activity(self, user_id, activity_date, **kwargs):
        activity = DailyActivity(
            user_id=user_id,
            activity_date=activity_date,
            total_steps=kwargs.get('total_steps', 0),
            total_distance=kwargs.get('total_distance', 0.0),
            very_active_minutes=kwargs.get('very_active_minutes', 0),
            fairly_active_minutes=kwargs.get('fairly_active_minutes', 0),
            lightly_active_minutes=kwargs.get('lightly_active_minutes', 0),
            sedentary_minutes=kwargs.get('sedentary_minutes', 0),
            calories=kwargs.get('calories', 0)
        )
        db.session.add(activity)
        db.session.commit()

    def store_sleep_data(self, user_id, sleep_date, **kwargs):
        sleep = SleepData(
            user_id=user_id,
            sleep_date=sleep_date,
            total_sleep_records=kwargs.get('total_sleep_records', 1),
            total_minutes_asleep=kwargs.get('total_minutes_asleep', 0),
            total_time_in_bed=kwargs.get('total_time_in_bed', 0),
            sleep_efficiency=kwargs.get('sleep_efficiency', 0.0)
        )
        db.session.add(sleep)
        db.session.commit()

    def get_user_health_data(self, user_id, days=30):
        cutoff_date = datetime.utcnow()
        # In SQLite/Postgres dates, simplify to a generic query
        # Since Date/DateTime math differs by dialect, we can fetch all or handle simply
        
        hr_query = HeartRateData.query.filter_by(user_id=user_id).order_by(HeartRateData.timestamp.desc()).limit(1000).all()
        activity_query = DailyActivity.query.filter_by(user_id=user_id).order_by(DailyActivity.activity_date.desc()).limit(days).all()
        sleep_query = SleepData.query.filter_by(user_id=user_id).order_by(SleepData.sleep_date.desc()).limit(days).all()
        
        def to_dict(row):
            return {c.name: getattr(row, c.name) for c in row.__table__.columns}

        return {
            'heart_rate': [{'timestamp': h.timestamp.isoformat(), 'heart_rate': h.heart_rate} for h in hr_query],
            'activity': [{'activity_date': a.activity_date.isoformat(), 'total_steps': a.total_steps, 'calories': a.calories, 'very_active_minutes': a.very_active_minutes, 'fairly_active_minutes': a.fairly_active_minutes} for a in activity_query],
            'sleep': [{'sleep_date': s.sleep_date.isoformat(), 'total_minutes_asleep': s.total_minutes_asleep, 'sleep_efficiency': s.sleep_efficiency} for s in sleep_query]
        }
    
    def store_health_prediction(self, user_id, health_score, risk_level, recommendations, confidence_score):
        prediction = HealthPrediction(
            user_id=user_id,
            prediction_date=datetime.utcnow(),
            health_score=health_score,
            risk_level=risk_level,
            recommendations=recommendations,
            confidence_score=confidence_score
        )
        db.session.add(prediction)
        db.session.commit()

# Initialize global wrapper for backward compatibility
db_manager = DatabaseManager()