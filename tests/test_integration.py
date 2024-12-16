# tests/test_integration.py
import pytest
from src.bot.core import JobApplicationBot

@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_application():
    bot = JobApplicationBot()
    
    test_resume = {
        "name": "Test User",
        "email": "test@example.com",
        "experience": ["Software Engineer", "Developer"]
    }
    
    result = await bot.apply_to_job(
        job_url="https://example.com/job",
        resume_data=test_resume
    )
    
    assert result.success is True
    assert result.application_id is not None