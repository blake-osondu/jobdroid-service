
# src/bot/__init__.py
"""
Bot core functionality
"""
from .core import JobApplicationBot
from .parsers import IndeedParser
from .parsers import LinkedInParser
from .automation import AutomationSession
from .ml import FormDetector
from .models.job_posting import JobPosting

__all__ = [
    'JobApplicationBot',
    'IndeedParser',
    'LinkedInParser',
    'AutomationSession',
    'FormDetector',
    'JobPosting'
]