from pydantic import BaseModel, EmailStr, HttpUrl, Field, validator
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime
import re

class JobPreferences(BaseModel):
    job_titles: List[str] = Field(..., min_items=1, max_items=10)
    locations: List[str] = Field(..., min_items=1, max_items=5)
    remote_preference: bool = True
    min_salary: Optional[int] = Field(None, ge=0)
    max_salary: Optional[int] = Field(None, ge=0)
    experience_level: str = Field(..., regex='^(Entry|Mid|Senior|Lead|Executive)$')
    industry_preferences: List[str] = []
    excluded_companies: List[str] = []
    
    @validator('max_salary')
    def validate_salary_range(cls, v, values):
        if v and values.get('min_salary') and v < values['min_salary']:
            raise ValueError('max_salary must be greater than min_salary')
        return v

class AutomationPreferences(BaseModel):
    class FrequencyType(str, Enum):
        DAILY = "daily"
        WEEKLY = "weekly"
        MONTHLY = "monthly"

    max_applications_per_day: int = Field(..., ge=1, le=50)
    preferred_time_slots: List[str] = Field(..., min_items=1)
    application_frequency: FrequencyType
    platforms: List[str] = Field(..., min_items=1)
    auto_cover_letter: bool = True
    follow_up_enabled: bool = True
    
    @validator('preferred_time_slots')
    def validate_time_slots(cls, v):
        time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]-([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
        for slot in v:
            if not time_pattern.match(slot):
                raise ValueError(f'Invalid time slot format: {slot}. Use HH:MM-HH:MM format')
        return v

class Education(BaseModel):
    degree: str
    field_of_study: str
    institution: str
    graduation_year: int
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)

class Experience(BaseModel):
    title: str
    company: str
    location: str
    start_date: datetime
    end_date: Optional[datetime]
    current: bool = False
    description: str
    skills: List[str]

class ResumeData(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str = Field(..., regex=r'^\+?1?\d{9,15}$')
    location: str
    linkedin_url: Optional[HttpUrl]
    portfolio_url: Optional[HttpUrl]
    summary: str = Field(..., max_length=2000)
    education: List[Education]
    experience: List[Experience]
    skills: List[str] = Field(..., min_items=1)
    certifications: List[str] = []
    
    @validator('experience')
    def validate_experience_dates(cls, v):
        for exp in v:
            if exp.end_date and exp.end_date < exp.start_date:
                raise ValueError('End date must be after start date')
            if exp.current and exp.end_date:
                raise ValueError('Current position cannot have an end date')
        return v

class SubscriptionTier(str, Enum):
    FREE = "free"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class UserProfile(BaseModel):
    user_id: str
    email: EmailStr
    subscription_tier: SubscriptionTier
    resume_data: ResumeData
    job_preferences: JobPreferences
    automation_preferences: AutomationPreferences
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AutomationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class ApplicationResult(BaseModel):
    job_id: str
    company: str
    position: str
    application_url: HttpUrl
    status: str
    applied_at: datetime
    error_message: Optional[str]

class AutomationSession(BaseModel):
    session_id: str
    user_id: str
    status: AutomationStatus
    start_time: datetime
    end_time: Optional[datetime]
    applications_submitted: int = 0
    applications_failed: int = 0
    results: List[ApplicationResult] = []
    error_log: List[str] = []

class AutomationRequest(BaseModel):
    user_id: str
    resume_version: Optional[str]
    override_preferences: Optional[Dict] = None
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user123",
                "resume_version": "tech_v2",
                "override_preferences": {
                    "max_applications_per_day": 20,
                    "platforms": ["LinkedIn", "Indeed"]
                }
            }
        }

class AutomationResponse(BaseModel):
    session_id: str
    status: AutomationStatus
    message: str
    estimated_completion: Optional[datetime]

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
