# src/bot/parsers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class JobPosting:
    title: str
    company: str
    location: str
    description: str
    requirements: List[str]
    salary_range: Optional[tuple]
    application_url: str
    source: str

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