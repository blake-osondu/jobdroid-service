# tests/test_parsers.py
import pytest
from src.bot.parsers.indeed import IndeedParser
from src.bot.parsers.linkedin import LinkedInParser

@pytest.mark.asyncio
async def test_indeed_parser():
    parser = IndeedParser({})
    
    # Test job search
    search_criteria = {
        "title": "Software Engineer",
        "location": "Remote"
    }
    
    results = await parser.search_jobs(search_criteria)
    assert isinstance(results, list)
    
    if results:
        job = results[0]
        assert "title" in job
        assert "company" in job
        assert "location" in job

@pytest.mark.asyncio
async def test_job_parsing():
    parser = IndeedParser({})
    test_url = "https://www.indeed.com/test-job"
    
    job_details = await parser.parse_job_details(test_url)
    assert job_details is not None
    assert hasattr(job_details, "title")
    assert hasattr(job_details, "company")