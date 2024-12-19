from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
import random
from .base import BaseParser
from ..models.job_posting import JobPosting

class IndeedParser(BaseParser):
    def __init__(self, config: dict):
        """
        Initialize Indeed parser with configuration
        """
        self.base_url = "https://www.indeed.com"
        self.config = config
        self.setup_browser()
        
    def setup_browser(self):
        """
        Configure webdriver with anti-detection measures
        """
        options = webdriver.ChromeOptions()
        
        # Anti-detection settings
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Add random user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        self.driver = webdriver.Chrome(options=options)
        
    async def search_jobs(self, criteria: dict) -> List[JobPosting]:
        """
        Search for jobs based on given criteria
        """
        try:
            # Construct search URL
            search_url = self._build_search_url(criteria)
            self.driver.get(search_url)
            
            # Wait for job cards to load
            await self._wait_for_elements("job_card")
            
            # Extract job listings
            job_listings = []
            page = 1
            
            while page <= self.config.get('max_pages', 3):
                # Get job cards on current page
                job_cards = self.driver.find_elements(By.CLASS_NAME, 'job_card')
                
                for card in job_cards:
                    try:
                        job_data = self._extract_job_card_data(card)
                        if job_data and self._matches_criteria(job_data, criteria):
                            job_listings.append(job_data)
                    except Exception as e:
                        print(f"Error extracting job card: {e}")
                        continue
                
                # Check for next page
                if not self._go_to_next_page():
                    break
                    
                page += 1
                # Random delay between pages
                time.sleep(random.uniform(2, 5))
            
            return job_listings
            
        except Exception as e:
            print(f"Error in search_jobs: {e}")
            return []
            
    async def parse_job_details(self, url: str) -> Optional[JobPosting]:
        """
        Parse detailed job information from job posting page
        """
        try:
            self.driver.get(url)
            await self._wait_for_elements("job-details")
            
            # Extract detailed job information
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            return JobPosting(
                title=self._get_text(soup, '.jobsearch-JobInfoHeader-title'),
                company=self._get_text(soup, '.jobsearch-InlineCompanyRating-companyHeader'),
                location=self._get_text(soup, '.jobsearch-JobInfoHeader-subtitle .jobsearch-JobInfoHeader-subtitle-location'),
                description=self._get_text(soup, '#jobDescriptionText'),
                requirements=self._extract_requirements(soup),
                salary_range=self._extract_salary(soup),
                application_url=url,
                source='Indeed'
            )
            
        except Exception as e:
            print(f"Error parsing job details: {e}")
            return None
            
    def _build_search_url(self, criteria: dict) -> str:
        """
        Build Indeed search URL from criteria
        """
        base_url = f"{self.base_url}/jobs?"
        params = {
            'q': criteria.get('keywords', ''),
            'l': criteria.get('location', ''),
            'radius': criteria.get('radius', '25'),
            'jt': criteria.get('job_type', ''),
            'fromage': criteria.get('posted_days', ''),
        }
        
        return base_url + '&'.join([f"{k}={v}" for k, v in params.items() if v])
        
    def _extract_job_card_data(self, card) -> Optional[JobPosting]:
        """
        Extract job information from a job card element
        """
        try:
            title = card.find_element(By.CLASS_NAME, 'jobTitle').text
            company = card.find_element(By.CLASS_NAME, 'companyName').text
            location = card.find_element(By.CLASS_NAME, 'companyLocation').text
            
            # Get job URL
            url_element = card.find_element(By.CSS_SELECTOR, 'h2.jobTitle a')
            url = url_element.get_attribute('href')
            
            return JobPosting(
                title=title,
                company=company,
                location=location,
                description='',  # Will be filled in detailed parse
                requirements=[],
                salary_range=self._extract_salary_from_card(card),
                application_url=url,
                source='Indeed'
            )
            
        except Exception as e:
            print(f"Error extracting job card data: {e}")
            return None
            
    def _extract_requirements(self, soup) -> List[str]:
        """
        Extract job requirements from job description
        """
        requirements = []
        description = soup.find(id='jobDescriptionText')
        
        if description:
            # Look for common requirement indicators
            requirement_sections = description.find_all(['ul', 'ol'])
            for section in requirement_sections:
                requirements.extend([li.text.strip() for li in section.find_all('li')])
                
        return requirements
        
    def _extract_salary(self, soup) -> Optional[tuple]:
        """
        Extract salary information from Indeed job posting
        Returns tuple of (min_salary, max_salary, period) or None if not found
        period can be 'year', 'month', 'week', 'hour'
        """
        try:
            salary_element = soup.find(class_='jobsearch-JobMetadataHeader-item')
            if not salary_element or '$' not in salary_element.text:
                return None

            salary_text = salary_element.text.strip().lower()
            
            # Remove common prefixes
            salary_text = salary_text.replace('estimated', '').replace('salary', '').strip()
            
            # Determine period
            period = 'year'  # default
            if 'hour' in salary_text or '/hr' in salary_text:
                period = 'hour'
            elif 'month' in salary_text:
                period = 'month'
            elif 'week' in salary_text:
                period = 'week'
                
            # Extract numbers
            import re
            numbers = re.findall(r'\$[\d,]+(?:\.\d{2})?', salary_text)
            if not numbers:
                return None
                
            # Convert string numbers to float
            amounts = []
            for num in numbers:
                # Remove $ and commas, convert to float
                amount = float(num.replace('$', '').replace(',', ''))
                amounts.append(amount)
                
            if len(amounts) == 0:
                return None
            elif len(amounts) == 1:
                # Single value - use as both min and max
                return (amounts[0], amounts[0], period)
            else:
                # Range - use min and max values
                return (min(amounts), max(amounts), period)
                
        except Exception as e:
            self.logger.error(f"Error parsing salary: {e}")
            return None

    def _normalize_salary(self, salary_tuple: Optional[tuple]) -> Optional[tuple]:
        """
        Normalize salary to yearly amount
        Returns (min_yearly, max_yearly) or None
        """
        if not salary_tuple:
            return None
            
        min_amount, max_amount, period = salary_tuple
        
        # Convert to yearly based on period
        multipliers = {
            'hour': 2080,  # 40 hours/week * 52 weeks
            'week': 52,
            'month': 12,
            'year': 1
        }
        
        multiplier = multipliers.get(period, 1)
        return (
            min_amount * multiplier,
            max_amount * multiplier
        )
        
    async def _wait_for_elements(self, class_name: str, timeout: int = 10):
        """
        Wait for elements to load
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, class_name))
            )
        except TimeoutException:
            print(f"Timeout waiting for {class_name}")
            
    def _matches_criteria(self, job: JobPosting, criteria: dict) -> bool:
        """
        Check if job matches search criteria
        Returns True if job matches all specified criteria, False otherwise
        """
        try:
            # Basic validation first
            if not self.validate_posting(vars(job)):
                return False
            
            # Title and description matching for keywords
            if 'keywords' in criteria:
                keywords = criteria['keywords'].lower().split()
                searchable_text = f"{job.title} {job.description}".lower()
                if not all(keyword in searchable_text for keyword in keywords):
                    return False
            
            # Location matching
            if 'location' in criteria:
                # Handle remote positions
                if 'remote' in criteria['location'].lower():
                    if not ('remote' in job.location.lower() or 'remote' in job.title.lower()):
                        return False
                # Handle regular locations
                elif not any(loc.lower() in job.location.lower() 
                           for loc in criteria['location'].split(',')):
                    return False
            
            # Salary range matching
            if 'salary_range' in criteria and job.salary_range:
                min_desired, max_desired = criteria['salary_range']
                min_actual, max_actual = self._normalize_salary(job.salary_range)
                
                # Check if salary ranges overlap
                if max_actual < min_desired or min_actual > max_desired:
                    return False
            
            # Experience level matching
            if 'experience_level' in criteria:
                exp_level = criteria['experience_level'].lower()
                description_lower = job.description.lower()
                
                experience_patterns = {
                    'entry': ['entry level', 'junior', '0-2 years', 'no experience'],
                    'mid': ['mid level', 'intermediate', '2-5 years', '3-5 years'],
                    'senior': ['senior', 'lead', '5+ years', '7+ years'],
                    'executive': ['executive', 'director', 'head of', 'vp', 'chief']
                }
                
                if not any(pattern in description_lower 
                          for pattern in experience_patterns.get(exp_level, [])):
                    return False
            
            # Job type matching (full-time, part-time, contract)
            if 'job_type' in criteria:
                job_type = criteria['job_type'].lower()
                if job_type not in job.title.lower() and job_type not in job.description.lower():
                    return False
            
            # Company type/industry matching
            if 'industry' in criteria:
                industries = [ind.lower() for ind in criteria['industry'].split(',')]
                if not any(ind in job.description.lower() for ind in industries):
                    return False
            
            # Required skills matching
            if 'required_skills' in criteria:
                required_skills = [skill.lower() for skill in criteria['required_skills']]
                job_text = f"{job.title} {job.description}".lower()
                if not all(skill in job_text for skill in required_skills):
                    return False
            
            # Education requirements matching
            if 'education' in criteria:
                education_level = criteria['education'].lower()
                education_patterns = {
                    'high school': ['high school', 'ged'],
                    'associate': ['associate', 'associate\'s', '2 year degree'],
                    'bachelor': ['bachelor', 'bachelor\'s', '4 year degree', 'bs', 'ba'],
                    'master': ['master', 'master\'s', 'ms', 'ma'],
                    'phd': ['phd', 'doctorate', 'doctoral']
                }
                
                if not any(pattern in job.description.lower() 
                          for pattern in education_patterns.get(education_level, [])):
                    return False
            
            # Posted date matching
            if 'posted_within_days' in criteria and hasattr(job, 'posted_date'):
                from datetime import datetime, timedelta
                max_age = timedelta(days=criteria['posted_within_days'])
                if datetime.now() - job.posted_date > max_age:
                    return False
            
            # If all criteria matched (or no criteria specified)
            return True
            
        except Exception as e:
            self.logger.error(f"Error in _matches_criteria: {e}")
            return False
        
    def cleanup(self):
        """
        Clean up resources
        """
        if self.driver:
            self.driver.quit()

    def validate_posting(self, posting) -> bool:
        """
        Validate if a job posting meets the criteria
        """
        try:
            required_fields = ['title', 'company', 'location']
            return all(posting.get(field) for field in required_fields)
        except Exception as e:
            self.logger.error(f"Error validating posting: {e}")
            return False
