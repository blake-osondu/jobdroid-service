# src/bot/parsers/linkedin.py
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import logging
import re
from .base import BaseParser
from ..models.job_posting import JobPosting

class LinkedInParser(BaseParser):
    def __init__(self, credentials: dict):
        self.credentials = credentials
        self.logger = logging.getLogger(__name__)
        self.setup_browser()
        self.is_logged_in = False
        
    def setup_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
    async def _ensure_logged_in(self):
        """Ensure we're logged into LinkedIn"""
        if self.is_logged_in:
            return True
            
        try:
            self.driver.get("https://www.linkedin.com/login")
            
            # Fill in credentials
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.send_keys(self.credentials['email'])
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(self.credentials['password'])
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Wait for successful login
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".global-nav"))
            )
            
            self.is_logged_in = True
            return True
            
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False
        
    async def search_jobs(self, criteria: dict) -> List[JobPosting]:
        """Search for jobs based on given criteria"""
        try:
            if not await self._ensure_logged_in():
                return []
            
            # Construct search URL
            base_url = "https://www.linkedin.com/jobs/search/?"
            params = []
            
            if 'keywords' in criteria:
                params.append(f"keywords={criteria['keywords']}")
            if 'location' in criteria:
                params.append(f"location={criteria['location']}")
            if 'experience_level' in criteria:
                level_map = {
                    'entry': 1,
                    'mid': 2,
                    'senior': 3,
                    'executive': 4
                }
                if criteria['experience_level'] in level_map:
                    params.append(f"f_E={level_map[criteria['experience_level']]}")
            
            search_url = base_url + "&".join(params)
            self.driver.get(search_url)
            
            # Wait for job listings to load
            job_cards = self.wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".job-card-container")
                )
            )
            
            jobs = []
            for card in job_cards[:10]:  # Limit to first 10 results for now
                try:
                    job_id = card.get_attribute("data-job-id")
                    title = card.find_element(By.CSS_SELECTOR, ".job-card-list__title").text
                    company = card.find_element(By.CSS_SELECTOR, ".job-card-container__company-name").text
                    location = card.find_element(By.CSS_SELECTOR, ".job-card-container__metadata-item").text
                    
                    # Get job details
                    card.click()
                    job_details = await self.parse_job_details(job_id)
                    
                    if job_details and self._matches_criteria(job_details, criteria):
                        jobs.append(job_details)
                        
                except Exception as e:
                    self.logger.error(f"Error processing job card: {e}")
                    continue
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Job search failed: {e}")
            return []
        
    async def parse_job_details(self, job_id: str) -> Optional[JobPosting]:
        """Parse detailed job information"""
        try:
            # Wait for job details panel to load
            details_container = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".job-view-layout"))
            )
            
            # Extract basic information
            title = details_container.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__job-title").text
            company = details_container.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__company-name").text
            location = details_container.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__bullet").text
            
            # Get description
            description = details_container.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__job-description").text
            
            # Extract salary if available
            salary_range = None
            try:
                salary_element = details_container.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__salary-info")
                salary_range = self._parse_salary(salary_element.text)
            except NoSuchElementException:
                pass
            
            # Get job type
            job_type = None
            try:
                job_type = details_container.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__job-type").text
            except NoSuchElementException:
                pass
            
            # Get application URL
            apply_button = details_container.find_element(By.CSS_SELECTOR, ".jobs-apply-button")
            application_url = apply_button.get_attribute("href")
            
            # Create JobPosting object
            return JobPosting(
                title=title,
                company=company,
                location=location,
                description=description,
                application_url=application_url,
                source="LinkedIn",
                salary_range=salary_range,
                job_type=job_type,
                posted_date=datetime.now(),  # LinkedIn doesn't always show exact date
                requirements=self._extract_requirements(description)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse job details: {e}")
            return None
        
    def validate_posting(self, posting: Dict) -> bool:
        """Validate if a job posting meets basic requirements"""
        try:
            # Check required fields
            required_fields = ['title', 'company', 'location', 'description', 'application_url']
            if not all(field in posting and posting[field] for field in required_fields):
                return False
            
            # Validate URL format
            if not posting['application_url'].startswith(('http://', 'https://')):
                return False
            
            # Validate content lengths
            if len(posting['title']) < 3 or len(posting['description']) < 50:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
            
    def _parse_salary(self, salary_text: str) -> Optional[tuple]:
        """Parse salary information from text"""
        try:
            # Remove currency symbols and convert to numbers
            numbers = re.findall(r'[\d,]+', salary_text)
            if len(numbers) >= 2:
                min_salary = float(numbers[0].replace(',', ''))
                max_salary = float(numbers[1].replace(',', ''))
                
                # Determine period (year, month, hour)
                period = 'year'  # Default
                if 'hour' in salary_text.lower() or '/hr' in salary_text.lower():
                    period = 'hour'
                elif 'month' in salary_text.lower():
                    period = 'month'
                
                return (min_salary, max_salary, period)
                
        except Exception as e:
            self.logger.error(f"Salary parsing error: {e}")
        
        return None
        
    def _extract_requirements(self, description: str) -> List[str]:
        """Extract requirements from job description"""
        requirements = []
        
        # Look for common requirement patterns
        patterns = [
            r'Requirements:.*?(?=\n\n|\Z)',
            r'Qualifications:.*?(?=\n\n|\Z)',
            r'Skills:.*?(?=\n\n|\Z)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description, re.DOTALL | re.IGNORECASE)
            if matches:
                # Split into bullet points or lines
                items = re.split(r'[•\-\*]|\d+\.', matches[0])
                requirements.extend([item.strip() for item in items if item.strip()])
        
        return requirements
        
    def __del__(self):
        """Clean up browser when done"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except Exception:
            pass