from pydantic import BaseModel, Field
from typing import Optional, List

class BLEDataPoint(BaseModel):
    timestamp: str
    heart_rate: Optional[int] = None
    steps: Optional[int] = None
    calories: Optional[float] = None
    spo2: Optional[float] = None
    temperature: Optional[float] = None
    hrv: Optional[float] = None

class BLEReadingBatch(BaseModel):
    device_id: str = Field(..., description="MAC address or unique ID of the device")
    readings: List[BLEDataPoint]

class DeviceConnectRequest(BaseModel):
    device_address: str = Field(..., description="MAC address or unique ID of the device to connect")
    device_name: str = Field('Unknown Device', description="Human readable name")
    device_type: str = Field('fitness_tracker', description="Type of device (e.g., fitness_tracker, smartwatch)")

class PredictHealthScoreRequest(BaseModel):
    TotalSteps: int = Field(..., ge=0, description="Total daily steps")
    Calories: float = Field(..., ge=0, description="Total calories burned")
    SedentaryMinutes: int = Field(..., ge=0, description="Total sedentary minutes")
    SleepHours: float = Field(0.0, ge=0, description="Total sleep duration in hours")
    VeryActiveMinutes: int = Field(0, ge=0, description="Very active minutes")
    FairlyActiveMinutes: int = Field(0, ge=0, description="Fairly active minutes")
    hr_avg: float = Field(0.0, ge=0, description="Average heart rate")
