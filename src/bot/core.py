# src/bot/core.py
from typing import Dict, List, Optional
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from .parsers.indeed import IndeedParser
from .parsers.linkedin import LinkedInParser
from .automation.session import AutomationSession
from .ml.form_detector import FormDetector
from ..utils.proxy import ProxyRotator
from ..utils.logger import JobBotLogger

@dataclass
class ApplicationResult:
    job_id: str
    status: str
    platform: str
    company: str
    position: str
    applied_at: datetime
    error: Optional[str] = None

class JobApplicationBot:
    def __init__(self, config: Dict):
        """Initialize the job application bot with configuration"""
        self.config = config
        self.logger = JobBotLogger(__name__)
        self.proxy_rotator = ProxyRotator()
        self.form_detector = FormDetector()
        
        # Initialize platform parsers
        self.parsers = {
            'linkedin': LinkedInParser(config['platforms']['linkedin']),
            'indeed': IndeedParser(config['platforms']['indeed'])
        }
        
        # Track application statistics
        self.stats = {
            'total_attempts': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }

    async def initialize(self) -> bool:
        """Initialize bot components and connections"""
        try:
            # Load proxy configuration
            if self.config['proxy']['enabled']:
                await self.proxy_rotator.load_proxies_from_file(
                    self.config['proxy']['proxy_list']
                )
            
            # Initialize automation session
            self.session = await AutomationSession(self.config).initialize()
            
            # Test platform connections
            for platform, parser in self.parsers.items():
                if not await self._test_platform_connection(platform):
                    self.logger.error(f"Failed to connect to {platform}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    async def start_automation(self, user_preferences: Dict) -> None:
        """Start the automated job application process"""
        try:
            self.logger.info("Starting automation process")
            
            # Find matching jobs across platforms
            jobs = await self._find_matching_jobs(user_preferences)
            self.logger.info(f"Found {len(jobs)} matching jobs")
            
            # Process each job
            results = []
            for job in jobs:
                if await self._should_apply(job):
                    result = await self._process_job_application(job)
                    results.append(result)
                    
                    # Respect rate limits
                    await self._handle_rate_limiting()
            
            # Update statistics
            self._update_stats(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Automation failed: {e}")
            raise

    async def _find_matching_jobs(self, preferences: Dict) -> List[Dict]:
        """Find jobs matching user preferences across platforms"""
        matching_jobs = []
        
        for platform, parser in self.parsers.items():
            if not self.config['platforms'][platform]['enabled']:
                continue
                
            try:
                platform_jobs = await parser.search_jobs(preferences)
                matching_jobs.extend(platform_jobs)
            except Exception as e:
                self.logger.error(f"Job search failed for {platform}: {e}")
        
        return self._filter_jobs(matching_jobs, preferences)

    async def _process_job_application(self, job: Dict) -> ApplicationResult:
        """Process a single job application"""
        try:
            # Get working proxy
            proxy = await self.proxy_rotator.get_working_proxy()
            if proxy:
                self.session.update_proxy(proxy)
            
            # Initialize application result
            result = ApplicationResult(
                job_id=job['id'],
                status='pending',
                platform=job['platform'],
                company=job['company'],
                position=job['title'],
                applied_at=datetime.now()
            )
            
            # Navigate to job page
            if not await self.session.navigate_to_job(job['url']):
                raise Exception("Failed to navigate to job page")
            
            # Detect and fill application form
            form_fields = await self.form_detector.detect_fields(
                await self.session.get_page_source()
            )
            
            if not form_fields:
                raise Exception("No application form detected")
            
            # Fill and submit application
            if await self.session.fill_application_form(form_fields):
                result.status = 'success'
                self.stats['successful'] += 1
            else:
                result.status = 'failed'
                result.error = "Form submission failed"
                self.stats['failed'] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Application failed: {e}")
            return ApplicationResult(
                job_id=job['id'],
                status='error',
                platform=job['platform'],
                company=job['company'],
                position=job['title'],
                applied_at=datetime.now(),
                error=str(e)
            )

    def _filter_jobs(self, jobs: List[Dict], preferences: Dict) -> List[Dict]:
        """Filter jobs based on user preferences"""
        filtered_jobs = []
        
        for job in jobs:
            if self._job_matches_preferences(job, preferences):
                filtered_jobs.append(job)
        
        return filtered_jobs

    def _job_matches_preferences(self, job: Dict, preferences: Dict) -> bool:
        """Check if job matches user preferences"""
        # Check required keywords
        if preferences.get('required_keywords'):
            if not any(keyword.lower() in job['title'].lower() 
                      for keyword in preferences['required_keywords']):
                return False
        
        # Check excluded keywords
        if preferences.get('excluded_keywords'):
            if any(keyword.lower() in job['title'].lower() 
                  for keyword in preferences['excluded_keywords']):
                return False
        
        # Check location preferences
        if preferences.get('locations'):
            if not any(location.lower() in job.get('location', '').lower() 
                      for location in preferences['locations']):
                return False
        
        # Check salary range if available
        if preferences.get('min_salary') and job.get('salary'):
            if job['salary'] < preferences['min_salary']:
                return False
        
        return True

    async def _handle_rate_limiting(self) -> None:
        """Handle rate limiting between applications"""
        delay = self.config['bot']['rate_limits']['delay_between_applications']
        await asyncio.sleep(delay)

    async def _test_platform_connection(self, platform: str) -> bool:
        """Test connection to job platform"""
        try:
            parser = self.parsers[platform]
            return await parser.test_connection()
        except Exception as e:
            self.logger.error(f"Platform connection test failed for {platform}: {e}")
            return False

    def _update_stats(self, results: List[ApplicationResult]) -> None:
        """Update application statistics"""
        self.stats['total_attempts'] += len(results)
        self.stats['successful'] += len([r for r in results if r.status == 'success'])
        self.stats['failed'] += len([r for r in results if r.status == 'failed'])
        
        # Track errors
        errors = [r for r in results if r.error]
        for error in errors:
            self.stats['errors'].append({
                'job_id': error.job_id,
                'company': error.company,
                'error': error.error,
                'timestamp': error.applied_at
            })

    def get_stats(self) -> Dict:
        """Get current application statistics"""
        return {
            **self.stats,
            'success_rate': self.stats['successful'] / self.stats['total_attempts'] 
                          if self.stats['total_attempts'] > 0 else 0
        }

    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            await self.session.cleanup()
            self.logger.info("Bot cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")