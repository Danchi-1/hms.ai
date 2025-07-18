import asyncio
import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import threading
import time
from dataclasses import dataclass, field
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class HealthDataPoint:
    """Structured health data point"""
    user_id: int
    device_address: str
    device_type: str
    measurement_type: str
    value: float
    timestamp: datetime
    confidence: float = 1.0
    raw_data: str = ""
    metadata: dict = field(default_factory=dict)

class HealthDataCollector:
    """
    Orchestrates health data collection from BLE devices and other sources
    Handles validation, buffering, and storage of health metrics
    """
    
    def __init__(self, db_manager, validator=None, buffer_size: int = 1000):
        self.db_manager = db_manager
        self.validator = validator
        self.buffer_size = buffer_size
        
        # Data buffers for different measurement types
        self.data_buffers = {
            'heart_rate': deque(maxlen=buffer_size),
            'steps': deque(maxlen=buffer_size),
            'sleep': deque(maxlen=buffer_size),
            'activity': deque(maxlen=buffer_size),
            'weight': deque(maxlen=buffer_size),
            'blood_pressure': deque(maxlen=buffer_size)
        }
        
        # Device management
        self.connected_devices = {}
        self.device_users = {}  # Map device addresses to user IDs
        
        # Collection statistics
        self.collection_stats = defaultdict(int)
        
        # Background processing
        self.is_processing = False
        self.processing_thread = None
        
        # Callbacks for real-time data
        self.data_callbacks = []
        
    def register_device(self, device_address: str, user_id: int, device_type: str):
        """Register a device with a specific user"""
        self.device_users[device_address] = user_id
        self.connected_devices[device_address] = {
            'user_id': user_id,
            'device_type': device_type,
            'connected_at': datetime.now(),
            'last_data': None,
            'data_count': 0
        }
        logger.info(f"Registered device {device_address} for user {user_id}")
    
    def unregister_device(self, device_address: str):
        """Unregister a device"""
        if device_address in self.device_users:
            del self.device_users[device_address]
        if device_address in self.connected_devices:
            del self.connected_devices[device_address]
        logger.info(f"Unregistered device {device_address}")
    
    def add_data_callback(self, callback: Callable):
        """Add callback for real-time data processing"""
        self.data_callbacks.append(callback)
    
    def collect_ble_data(self, raw_data: Dict):
        """
        Handle incoming BLE data
        
        Args:
            raw_data: Raw data from BLE device
        """
        try:
            # Extract device info
            device_address = raw_data.get('device_address')
            if not device_address or device_address not in self.device_users:
                logger.warning(f"Unknown device: {device_address}")
                return
            
            user_id = self.device_users[device_address]
            device_type = raw_data.get('device_type', 'unknown')
            measurement_type = raw_data.get('measurement_type', 'unknown')
            
            # Create structured data point
            data_point = HealthDataPoint(
                user_id=user_id,
                device_address=device_address,
                device_type=device_type,
                measurement_type=measurement_type,
                value=raw_data.get('value', 0),
                timestamp=datetime.fromisoformat(raw_data.get('timestamp', datetime.now().isoformat())),
                raw_data=raw_data.get('raw_data', ''),
                metadata=raw_data.get('metadata', {})
            )
            
            # Validate data if validator available
            if self.validator:
                is_valid, confidence = self.validator.validate_data_point(data_point)
                if not is_valid:
                    logger.warning(f"Invalid data point rejected: {data_point}")
                    self.collection_stats['rejected'] += 1
                    return
                data_point.confidence = confidence
            
            # Add to appropriate buffer
            buffer_key = measurement_type
            if buffer_key not in self.data_buffers:
                self.data_buffers[buffer_key] = deque(maxlen=self.buffer_size)
            
            self.data_buffers[buffer_key].append(data_point)
            
            # Update device stats
            if device_address in self.connected_devices:
                self.connected_devices[device_address]['last_data'] = datetime.now()
                self.connected_devices[device_address]['data_count'] += 1
            
            # Update collection stats
            self.collection_stats['total_collected'] += 1
            self.collection_stats[measurement_type] += 1
            
            # Trigger callbacks
            for callback in self.data_callbacks:
                try:
                    callback(data_point)
                except Exception as e:
                    logger.error(f"Error in data callback: {e}")
            
            logger.debug(f"Collected {measurement_type} data: {data_point.value}")
            
        except Exception as e:
            logger.error(f"Error collecting BLE data: {e}")
            self.collection_stats['errors'] += 1
    
    def collect_manual_data(self, user_id: int, measurement_type: str, value: float, 
                           timestamp: Optional[datetime] = None, metadata: Dict = {}):
        """
        Collect manually entered health data
        Args:
            user_id: User ID
            measurement_type: Type of measurement
            value: Measurement value
            timestamp: Optional timestamp (defaults to now)
            metadata: Additional metadata
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        data_point = HealthDataPoint(
            user_id=user_id,
            device_address='manual',
            device_type='manual_entry',
            measurement_type=measurement_type,
            value=value,
            timestamp=timestamp,
            metadata=metadata or {}
        )
        
        # Validate if validator available
        if self.validator:
            is_valid, confidence = self.validator.validate_data_point(data_point)
            if not is_valid:
                logger.warning(f"Invalid manual data rejected: {data_point}")
                return False
            data_point.confidence = confidence
        
        # Add to buffer
        buffer_key = measurement_type
        if buffer_key not in self.data_buffers:
            self.data_buffers[buffer_key] = deque(maxlen=self.buffer_size)
        
        self.data_buffers[buffer_key].append(data_point)
        
        # Update stats
        self.collection_stats['total_collected'] += 1
        self.collection_stats['manual_entries'] += 1
        self.collection_stats[measurement_type] += 1
        
        # Trigger callbacks
        for callback in self.data_callbacks:
            try:
                callback(data_point)
            except Exception as e:
                logger.error(f"Error in data callback: {e}")
        
        logger.info(f"Collected manual {measurement_type} data: {value}")
        return True
    
    def get_recent_data(self, measurement_type: str, limit: int = 100) -> List[HealthDataPoint]:
        """Get recent data points for a specific measurement type"""
        if measurement_type not in self.data_buffers:
            return []
        
        buffer = self.data_buffers[measurement_type]
        return list(buffer)[-limit:]
    
    def get_user_recent_data(self, user_id: int, measurement_type: str, 
                           limit: int = 100) -> List[HealthDataPoint]:
        """Get recent data points for a specific user and measurement type"""
        if measurement_type not in self.data_buffers:
            return []
        
        buffer = self.data_buffers[measurement_type]
        user_data = [dp for dp in buffer if dp.user_id == user_id]
        return user_data[-limit:]
    
    def _cleanup_old_data(self):
        """Cleanup old or irrelevant health data to avoid memory issues."""
        for buffer in self.data_buffers.values():
            buffer.clear()

    def start_background_processing(self):
        """Start background processing thread"""
        if self.is_processing:
            return
        
        self.is_processing = True
        
        def processing_worker():
            while self.is_processing:
                try:
                    # Process each buffer
                    for measurement_type, buffer in self.data_buffers.items():
                        if buffer:
                            self._process_buffer(measurement_type, buffer)
                    
                    # Store aggregated data
                    self._store_aggregated_data()
                    
                    # Clean old data
                    self._cleanup_old_data()
                    
                    time.sleep(30)  # Process every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Error in background processing: {e}")
                    time.sleep(60)  # Wait longer on error
        
        self.processing_thread = threading.Thread(target=processing_worker)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        logger.info("Started background data processing")
    
    def stop_background_processing(self):
        """Stop background processing"""
        self.is_processing = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        logger.info("Stopped background data processing")
    
    def _process_buffer(self, measurement_type: str, buffer: deque):
        """Process data in a specific buffer"""
        if not buffer:
            return
        
        # Store individual data points
        for data_point in list(buffer):
            self._store_data_point(data_point)
        
        # Clear processed data
        buffer.clear()
    
    def _store_data_point(self, data_point: HealthDataPoint):
        """Store individual data point in database"""
        try:
            if data_point.measurement_type == 'heart_rate':
                self.db_manager.store_heart_rate(
                    user_id=data_point.user_id,
                    timestamp=data_point.timestamp,
                    heart_rate=int(data_point.value),
                    device_id=data_point.device_address
                )
            elif data_point.measurement_type == 'steps':
                # For steps, we might need to aggregate daily
                self._store_daily_activity_data(data_point)
            elif data_point.measurement_type == 'sleep':
                self._store_sleep_data(data_point)
            
            logger.debug(f"Stored {data_point.measurement_type} data for user {data_point.user_id}")
            
        except Exception as e:
            logger.error(f"Error storing data point: {e}")
    
    def _store_daily_activity_data(self, data_point: HealthDataPoint):
        """Store daily activity data (steps, calories, etc.)"""
        try:
            activity_date = data_point.timestamp.date()
            
            # Get existing data for the day
            existing_data = self.db_manager.get_daily_activity(data_point.user_id, activity_date)
            
            # Update or create daily activity record
            activity_data = {
                'total_steps': int(data_point.value) if data_point.measurement_type == 'steps' else 0,
                'calories': int(data_point.value) if data_point.measurement_type == 'calories' else 0,
                'very_active_minutes': int(data_point.value) if data_point.measurement_type == 'very_active' else 0,
                'fairly_active_minutes': int(data_point.value) if data_point.measurement_type == 'fairly_active' else 0,
                'lightly_active_minutes': int(data_point.value) if data_point.measurement_type == 'lightly_active' else 0,
                'sedentary_minutes': int(data_point.value) if data_point.measurement_type == 'sedentary' else 0,
            }
            
            # Merge with existing data if available
            if existing_data:
                for key, value in activity_data.items():
                    if value > 0:  # Only update non-zero values
                        activity_data[key] = value
            
            self.db_manager.store_daily_activity(
                user_id=data_point.user_id,
                activity_date=activity_date,
                **activity_data
            )
            
        except Exception as e:
            logger.error(f"Error storing daily activity data: {e}")
    
    def _store_sleep_data(self, data_point: HealthDataPoint):
        """Store sleep data"""
        try:
            sleep_date = data_point.timestamp.date()
            
            sleep_data = {
                'total_minutes_asleep': int(data_point.value) if data_point.measurement_type == 'sleep_duration' else 0,
                'total_time_in_bed': int(data_point.value) if data_point.measurement_type == 'time_in_bed' else 0,
                'sleep_efficiency': float(data_point.value) if data_point.measurement_type == 'sleep_efficiency' else 0.0,
            }
            
            self.db_manager.store_sleep_data(
                user_id=data_point.user_id,
                sleep_date=sleep_date,
                **sleep_data
            )
            
        except Exception as e:
            logger.error(f"Error storing sleep data: {e}")
    
    def _store_aggregated_data(self):
        """Store aggregated data summaries"""
        try:
            # Create daily summaries for each user
            current_date = datetime.now().date()
            
            for user_id in set(self.device_users.values()):
                self._create_daily_summary(user_id, current_date)
                
        except Exception as e:
            logger.error(f"Error storing aggregated data: {e}")
    
    def _create_daily_summary(self, user_id: int, date):
        """Create daily summary for a user"""
        try:
            # Get all data for the day
            daily_data = defaultdict(list)
            
            for measurement_type, buffer in self.data_buffers.items():
                user_data = [dp for dp in buffer if dp.user_id == user_id and dp.timestamp.date() == date]
                if user_data:
                    daily_data[measurement_type] = user_data
            
            # Calculate summaries
            summary = {
                'user_id': user_id,
                'date': date,
                'data_points': len([dp for buffer in daily_data.values() for dp in buffer]),
                'measurements': list(daily_data.keys())
            }
            
            # Add measurement-specific summaries
            for measurement_type, data_points in daily_data.items():
                values = [dp.value for dp in data_points]
                if values:
                    summary[f'{measurement_type}_avg'] = sum(values) / len(values)
                    summary[f'{measurement_type}_min'] = min(values)
                    summary[f'{measurement_type}_max'] = max(values)
                    summary[f'{measurement_type}_count'] = len(values)

        except Exception as e:
            logger.error(f"Error creating daily summary for user {user_id} on {date}: {e}")
            return "Error {e} creating daily summary"