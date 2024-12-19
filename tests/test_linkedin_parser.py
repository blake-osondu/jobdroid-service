import pytest
from unittest.mock import Mock, patch
from selenium.webdriver.common.by import By
from bot.parsers.linkedin import LinkedInParser
from bot.models.job_posting import JobPosting

@pytest.fixture
def parser():
    credentials = {
        'email': 'test@example.com',
        'password': 'password123'
    }
    with patch('selenium.webdriver.Chrome') as mock_driver:
        parser = LinkedInParser(credentials)
        parser.driver = mock_driver
        parser.wait = Mock()
        yield parser

def test_validate_posting(parser):
    # Valid posting
    valid_posting = {
        'title': 'Software Engineer',
        'company': 'Tech Corp',
        'location': 'New York, NY',
        'description': 'We are looking for a software engineer with 5+ years of experience...',
        'application_url': 'https://example.com/apply'
    }
    assert parser.validate_posting(valid_posting) == True
    
    # Invalid posting (missing fields)
    invalid_posting = {
        'title': 'Software Engineer',
        'company': 'Tech Corp'
    }
    assert parser.validate_posting(invalid_posting) == False
    
    # Invalid posting (bad URL)
    invalid_url_posting = {
        **valid_posting,
        'application_url': 'not-a-url'
    }
    assert parser.validate_posting(invalid_url_posting) == False

def test_parse_salary(parser):
    test_cases = [
        (
            "$80,000 - $120,000 per year",
            (80000, 120000, 'year')
        ),
        (
            "$30 - $45 per hour",
            (30, 45, 'hour')
        ),
        (
            "Invalid salary text",
            None
        )
    ]
    
    for salary_text, expected in test_cases:
        result = parser._parse_salary(salary_text)
        assert result == expected

def test_extract_requirements(parser):
    description = """
    Requirements:
    • 5+ years of Python experience
    • Bachelor's degree in Computer Science
    • Experience with AWS
    
    Qualifications:
    • Strong communication skills
    • Agile experience
    """
    
    requirements = parser._extract_requirements(description)
    assert len(requirements) > 0
    assert "5+ years of Python experience" in requirements
    assert "Bachelor's degree in Computer Science" in requirements

if __name__ == "__main__":
    pytest.main([__file__])
