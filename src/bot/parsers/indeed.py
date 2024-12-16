from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
import random
from .base import BaseParser, JobPosting

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
        Extract salary information
        """
        salary_element = soup.find(class_='jobsearch-JobMetadataHeader-item')
        if salary_element and '$' in salary_element.text:
            # Parse salary range
            salary_text = salary_element.text
            # Add salary parsing logic here
            return None
        return None
        
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
        """
        # Add matching logic here
        return True
        
    def cleanup(self):
        """
        Clean up resources
        """
        if self.driver:
            self.driver.quit()
