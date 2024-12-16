from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc
from typing import Optional, Dict
import random
import time
import logging
from ..utils.proxy import ProxyRotator

class AutomationSession:
    def __init__(self, config: Dict):
        """
        Initialize automation session with configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.proxy_rotator = ProxyRotator(config.get('proxies', []))
        self.driver = None
        self.current_platform = None
        self.session_data = {}
        
    async def initialize(self, platform: str) -> bool:
        """
        Initialize browser session for specific platform
        """
        try:
            self.current_platform = platform
            self.driver = await self._setup_browser()
            await self._setup_platform_session(platform)
            return True
        except Exception as e:
            self.logger.error(f"Session initialization failed: {e}")
            return False

    async def _setup_browser(self) -> webdriver.Chrome:
        """
        Set up undetected Chrome browser with anti-detection measures
        """
        options = uc.ChromeOptions()
        
        # Anti-detection configurations
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        
        # Random window size
        window_sizes = [(1366, 768), (1920, 1080), (1440, 900)]
        window_size = random.choice(window_sizes)
        options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')
        
        # Add proxy if configured
        if self.config.get('use_proxies', False):
            proxy = self.proxy_rotator.get_next_proxy()
            if proxy:
                options.add_argument(f'--proxy-server={proxy}')
        
        return uc.Chrome(options=options)

    async def _setup_platform_session(self, platform: str) -> None:
        """
        Set up session for specific platform (LinkedIn, Indeed, etc.)
        """
        platform_configs = {
            'linkedin': {
                'login_url': 'https://www.linkedin.com/login',
                'credentials': self.config.get('linkedin_credentials')
            },
            'indeed': {
                'login_url': 'https://secure.indeed.com/account/login',
                'credentials': self.config.get('indeed_credentials')
            }
        }
        
        config = platform_configs.get(platform.lower())
        if config and config['credentials']:
            await self._login(config['login_url'], config['credentials'])

    async def _login(self, url: str, credentials: Dict) -> None:
        """
        Handle platform login
        """
        try:
            self.driver.get(url)
            await self._human_like_delay()
            
            # Wait for login form
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            
            # Simulate human-like typing
            username_field = self.driver.find_element(By.ID, "username")
            password_field = self.driver.find_element(By.ID, "password")
            
            await self._human_like_typing(username_field, credentials['username'])
            await self._human_like_typing(password_field, credentials['password'])
            
            # Find and click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "[type='submit']")
            await self._human_like_delay()
            login_button.click()
            
            # Wait for login completion
            await self._verify_login()
            
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            raise

    async def navigate(self, url: str) -> bool:
        """
        Navigate to URL with error handling and retry logic
        """
        max_retries = 3
        current_try = 0
        
        while current_try < max_retries:
            try:
                self.driver.get(url)
                await self._human_like_delay()
                return True
            except WebDriverException as e:
                current_try += 1
                self.logger.warning(f"Navigation failed (attempt {current_try}): {e}")
                if current_try == max_retries:
                    return False
                await self._handle_navigation_error()

    async def _human_like_delay(self) -> None:
        """
        Add random delays to simulate human behavior
        """
        time.sleep(random.uniform(1.5, 4.0))

    async def _human_like_typing(self, element, text: str) -> None:
        """
        Simulate human-like typing
        """
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))

    async def _verify_login(self) -> bool:
        """
        Verify successful login
        """
        try:
            # Wait for login success indicators
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".profile-rail-card"))
            )
            return True
        except TimeoutException:
            self.logger.error("Login verification failed")
            return False

    async def _handle_navigation_error(self) -> None:
        """
        Handle navigation errors with recovery logic
        """
        if self.config.get('use_proxies', False):
            self.proxy_rotator.rotate_proxy()
            await self.initialize(self.current_platform)
        else:
            time.sleep(random.uniform(5, 10))

    def cleanup(self) -> None:
        """
        Clean up session resources
        """
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")

    async def get_page_source(self) -> Optional[str]:
        """
        Get current page source with error handling
        """
        try:
            return self.driver.page_source
        except Exception as e:
            self.logger.error(f"Failed to get page source: {e}")
            return None

    async def check_for_captcha(self) -> bool:
        """
        Check if current page has CAPTCHA
        """
        try:
            captcha_indicators = [
                "//iframe[contains(@src, 'captcha')]",
                "//div[contains(@class, 'captcha')]",
                "//img[contains(@src, 'captcha')]"
            ]
            
            for indicator in captcha_indicators:
                if len(self.driver.find_elements(By.XPATH, indicator)) > 0:
                    return True
            return False
        except Exception:
            return False
