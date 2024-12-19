# src/bot/parsers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from ..models.job_posting import JobPosting
class BaseParser(ABC):
    @abstractmethod
    async def search_jobs(self, criteria: dict) -> List[JobPosting]:
        pass
    
    @abstractmethod
    async def parse_job_details(self, url: str) -> JobPosting:
        pass
    
    @abstractmethod
    async def validate_posting(self, posting: JobPosting) -> bool:
        pass