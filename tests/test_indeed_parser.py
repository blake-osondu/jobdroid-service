import pytest
from bs4 import BeautifulSoup
from unittest.mock import Mock
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from bot.parsers.indeed import IndeedParser
from bot.models.job_posting import JobPosting

class TestIndeedParser(IndeedParser):
    """Test version of IndeedParser that doesn't require browser setup"""
    def __init__(self, config):
        self.config = config
        self.logger = Mock()
        # Skip browser setup
    
    def setup_browser(self):
        pass

@pytest.fixture
def parser():
    config = {'indeed': {'enabled': True}}
    return TestIndeedParser(config)

def test_salary_parsing(parser):
    test_cases = [
        # Test yearly salaries
        {
            'html': '<div class="jobsearch-JobMetadataHeader-item">$50,000 - $75,000 a year</div>',
            'expected': (50000, 75000, 'year')
        },
        # Test hourly rates
        {
            'html': '<div class="jobsearch-JobMetadataHeader-item">$20.50 - $25.75 /hr</div>',
            'expected': (20.50, 25.75, 'hour')
        },
        # Test single values
        {
            'html': '<div class="jobsearch-JobMetadataHeader-item">$65,000 a year</div>',
            'expected': (65000, 65000, 'year')
        },
        # Test monthly rates
        {
            'html': '<div class="jobsearch-JobMetadataHeader-item">$4,000 - $5,000 a month</div>',
            'expected': (4000, 5000, 'month')
        },
        # Test with estimated prefix
        {
            'html': '<div class="jobsearch-JobMetadataHeader-item">Estimated $70,000 - $90,000 a year</div>',
            'expected': (70000, 90000, 'year')
        },
        # Test invalid formats
        {
            'html': '<div class="jobsearch-JobMetadataHeader-item">Competitive salary</div>',
            'expected': None
        },
    ]
    
    for case in test_cases:
        soup = BeautifulSoup(case['html'], 'html.parser')
        result = parser._extract_salary(soup)
        assert result == case['expected'], f"Failed parsing: {case['html']}"
        
        if result:
            # Test salary normalization
            yearly = parser._normalize_salary(result)
            assert yearly is not None
            assert len(yearly) == 2
            assert yearly[0] > 0
            assert yearly[1] >= yearly[0]

def test_normalize_salary(parser):
    test_cases = [
        # (input_tuple, expected_yearly_tuple)
        ((20, 25, 'hour'), (41600, 52000)),  # 20-25/hr * 2080
        ((1000, 1200, 'week'), (52000, 62400)),  # weekly * 52
        ((4000, 5000, 'month'), (48000, 60000)),  # monthly * 12
        ((60000, 80000, 'year'), (60000, 80000)),  # already yearly
    ]
    
    for input_tuple, expected in test_cases:
        result = parser._normalize_salary(input_tuple)
        assert result == expected, f"Failed normalizing: {input_tuple}"

def test_matches_criteria(parser):
    # Create a sample job posting
    job = JobPosting(
        title="Senior Python Developer",
        company="Tech Corp",
        location="New York, NY (Remote)",
        description="""
        We're looking for a Senior Python Developer with 5+ years of experience.
        Must have Bachelor's degree in Computer Science or related field.
        Skills: Python, Django, AWS, Docker
        Full-time position
        Salary: $120,000 - $150,000/year
        """,
        requirements=["Python", "Django", "AWS"],
        salary_range=(120000, 150000, 'year'),
        application_url="https://example.com",
        source="Indeed"
    )
    
    test_cases = [
        # Test keywords matching
        (
            {'keywords': 'python developer'},
            True
        ),
        (
            {'keywords': 'java developer'},
            False
        ),
        
        # Test location matching
        (
            {'location': 'New York'},
            True
        ),
        (
            {'location': 'Remote'},
            True
        ),
        (
            {'location': 'San Francisco'},
            False
        ),
        
        # Test salary matching
        (
            {'salary_range': (100000, 160000)},
            True
        ),
        (
            {'salary_range': (160000, 200000)},
            False
        ),
        
        # Test experience level matching
        (
            {'experience_level': 'senior'},
            True
        ),
        (
            {'experience_level': 'entry'},
            False
        ),
        
        # Test job type matching
        (
            {'job_type': 'full-time'},
            True
        ),
        (
            {'job_type': 'contract'},
            False
        ),
        
        # Test required skills matching
        (
            {'required_skills': ['Python', 'Django']},
            True
        ),
        (
            {'required_skills': ['Python', 'Java']},
            False
        ),
        
        # Test education matching
        (
            {'education': 'bachelor'},
            True
        ),
        (
            {'education': 'phd'},
            False
        ),
        
        # Test multiple criteria
        (
            {
                'keywords': 'python',
                'location': 'New York',
                'experience_level': 'senior',
                'required_skills': ['Python', 'Django']
            },
            True
        )
    ]
    
    for criteria, expected in test_cases:
        result = parser._matches_criteria(job, criteria)
        assert result == expected, f"Failed matching criteria: {criteria}"

if __name__ == "__main__":
    pytest.main([__file__])
