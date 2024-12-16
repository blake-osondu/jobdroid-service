# src/bot/automation/__init__.py
"""
Automation components for job applications
"""
from .session import AutomationSession
from .form_filler import FormFiller

__all__ = [
    'AutomationSession',
    'FormFiller'
]