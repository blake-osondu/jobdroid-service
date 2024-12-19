# src/bot/core.py
from typing import Dict, List, Optional
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from bot.parsers.indeed import IndeedParser
from bot.parsers.linkedin import LinkedInParser
from bot.automation.session import AutomationSession
from bot.ml.form_detector import FormDetector, FormField
from utils.proxy import ProxyRotator
from utils.logger import JobBotLogger

@dataclass
class ApplicationResult:
    job_id: str
    status: str
    platform: str
    company: str
    position: str
    applied_at: datetime
    error: Optional[str] = None
    form_fields: Optional[Dict[str, List[FormField]]] = None

class JobApplicationBot:
    def __init__(self, config: Dict):
        """Initialize the job application bot with configuration"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.form_detector = FormDetector()
        self.session = None
        
        # Track application statistics
        self.stats = {
            'total_attempts': 0,
            'successful': 0,
            'failed': 0,
            'errors': [],
            'forms_detected': 0,
            'fields_detected': 0
        }
        
        # Initialize parsers only when needed
        self._parsers = {}

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
            # Initialize result
            result = ApplicationResult(
                job_id=job['id'],
                status='pending',
                platform=job['platform'],
                company=job['company'],
                position=job['title'],
                applied_at=datetime.now()
            )
            
            # Get page content
            page_source = await self.session.get_page_source()
            
            # Detect form fields
            detected_forms = await self.form_detector.detect_fields(page_source)
            
            if not detected_forms:
                raise Exception("No application form detected")
            
            # Update stats
            self.stats['forms_detected'] += len(detected_forms)
            for form in detected_forms:
                self.stats['fields_detected'] += (
                    len(form['required_fields']) + 
                    len(form['optional_fields']) + 
                    len(form['file_uploads'])
                )
            
            # Store detected fields in result
            result.form_fields = detected_forms[0]  # Use first form for now
            
            # Attempt to fill the form
            if await self._fill_application_form(result.form_fields):
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

    async def _fill_application_form(self, form_fields: Dict[str, List[FormField]]) -> bool:
        """Fill out the detected application form"""
        try:
            # Handle required fields first
            for field in form_fields['required_fields']:
                if not await self._fill_field(field):
                    self.logger.error(f"Failed to fill required field: {field.name}")
                    return False
            
            # Handle optional fields
            for field in form_fields['optional_fields']:
                try:
                    await self._fill_field(field)
                except Exception as e:
                    self.logger.warning(f"Failed to fill optional field {field.name}: {e}")
            
            # Handle file uploads
            for field in form_fields['file_uploads']:
                if 'resume' in field.name.lower():
                    if not await self._upload_resume(field):
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Form filling failed: {e}")
            return False

    async def _fill_field(self, field: FormField) -> bool:
        """Fill a single form field based on its type and purpose"""
        try:
            # Get field value from user profile
            value = self._get_field_value(field)
            
            # Fill the field using automation session
            await self.session.fill_field(
                field_name=field.name,
                field_type=field.field_type,
                value=value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to fill field {field.name}: {e}")
            return False

    def _get_field_value(self, field: FormField) -> str:
        """Get the appropriate value for a form field"""
        # This would come from user profile/preferences
        field_mapping = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '123-456-7890',
            'experience': '3-5',
            'education': "Bachelor's Degree"
        }
        
        # Try to match field purpose to value
        for purpose, patterns in self.form_detector.common_field_patterns.items():
            if any(pattern in field.name.lower() for pattern in patterns):
                return field_mapping.get(purpose, '')
        
        return ''

    async def _upload_resume(self, field: FormField) -> bool:
        """Upload resume to a file upload field"""
        try:
            resume_path = self.config.get('resume_path')
            if not resume_path:
                self.logger.error("No resume path configured")
                return False
            
            await self.session.upload_file(
                field_name=field.name,
                file_path=resume_path
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Resume upload failed: {e}")
            return False

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
        stats = {
            **self.stats,
            'success_rate': self.stats['successful'] / self.stats['total_attempts'] 
                          if self.stats['total_attempts'] > 0 else 0,
            'average_fields_per_form': self.stats['fields_detected'] / self.stats['forms_detected']
                                     if self.stats['forms_detected'] > 0 else 0
        }
        return stats

    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            await self.session.cleanup()
            self.logger.info("Bot cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")