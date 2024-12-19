from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime

@dataclass
class JobPosting:
    """
    Represents a job posting with all relevant information
    """
    title: str
    company: str
    location: str
    description: str
    application_url: str
    source: str  # e.g., "Indeed", "LinkedIn"
    requirements: Optional[List[str]] = None
    salary_range: Optional[Tuple[float, float, str]] = None  # (min, max, period)
    posted_date: Optional[datetime] = None
    job_type: Optional[str] = None  # e.g., "full-time", "contract"
    experience_level: Optional[str] = None
    education_level: Optional[str] = None
    industry: Optional[str] = None
    benefits: Optional[List[str]] = None
    remote: Optional[bool] = None
