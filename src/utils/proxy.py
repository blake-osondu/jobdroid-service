from typing import Optional, List, Dict
import aiohttp
import asyncio
from datetime import datetime, timedelta
import logging
import json
from dataclasses import dataclass

@dataclass
class Proxy:
    """Proxy data structure"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = 'http'
    is_active: bool = True
    last_used: Optional[datetime] = None
    fail_count: int = 0

class ProxyRotator:
    def __init__(self):
        """Initialize proxy rotator"""
        self.logger = logging.getLogger(__name__)
        self.proxies: List[Proxy] = []
        self.current_index = 0
        self.max_fails = 3
        self.test_urls = [
            'https://api.ipify.org?format=json',
            'https://httpbin.org/ip'
        ]

    def load_proxies_from_file(self, filepath: str) -> None:
        """Load proxies from a JSON configuration file"""
        try:
            with open(filepath, 'r') as file:
                proxy_list = json.load(file)
                
            for proxy_data in proxy_list:
                proxy = Proxy(
                    host=proxy_data['host'],
                    port=proxy_data['port'],
                    username=proxy_data.get('username'),
                    password=proxy_data.get('password'),
                    protocol=proxy_data.get('protocol', 'http')
                )
                self.proxies.append(proxy)
                
            self.logger.info(f"Loaded {len(self.proxies)} proxies")
        except Exception as e:
            self.logger.error(f"Failed to load proxies: {e}")
            raise

    async def test_proxy(self, proxy: Proxy) -> bool:
        """Test if proxy is working"""
        proxy_url = self._get_proxy_url(proxy)
        
        try:
            async with aiohttp.ClientSession() as session:
                for test_url in self.test_urls:
                    try:
                        async with session.get(
                            test_url,
                            proxy=proxy_url,
                            timeout=10
                        ) as response:
                            if response.status == 200:
                                proxy.fail_count = 0
                                proxy.last_used = datetime.now()
                                return True
                    except:
                        continue
                        
            proxy.fail_count += 1
            return False
            
        except Exception as e:
            self.logger.debug(f"Proxy test failed for {proxy.host}: {e}")
            proxy.fail_count += 1
            return False

    async def get_working_proxy(self) -> Optional[Proxy]:
        """Get next working proxy"""
        if not self.proxies:
            return None

        # Try each proxy until we find a working one
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            
            # Skip if proxy has failed too many times
            if proxy.fail_count >= self.max_fails:
                self._rotate_index()
                attempts += 1
                continue
                
            # Test the proxy
            if await self.test_proxy(proxy):
                return proxy
                
            self._rotate_index()
            attempts += 1
            
        self.logger.error("No working proxies available")
        return None

    def _get_proxy_url(self, proxy: Proxy) -> str:
        """Generate proxy URL string"""
        if proxy.username and proxy.password:
            return f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
        return f"{proxy.protocol}://{proxy.host}:{proxy.port}"

    def _rotate_index(self) -> None:
        """Rotate to next proxy index"""
        self.current_index = (self.current_index + 1) % len(self.proxies)

    def mark_proxy_failed(self, proxy: Proxy) -> None:
        """Mark a proxy as failed"""
        proxy.fail_count += 1
        if proxy.fail_count >= self.max_fails:
            self.logger.warning(f"Proxy {proxy.host} marked as inactive after {proxy.fail_count} failures")
            proxy.is_active = False

    async def refresh_proxies(self) -> None:
        """Test all proxies and refresh their status"""
        self.logger.info("Refreshing proxy pool...")
        
        tasks = [self.test_proxy(proxy) for proxy in self.proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        working_count = sum(1 for r in results if r is True)
        self.logger.info(f"Proxy refresh complete. {working_count}/{len(self.proxies)} proxies working")

    def get_stats(self) -> Dict:
        """Get proxy pool statistics"""
        active_proxies = [p for p in self.proxies if p.is_active]
        return {
            "total_proxies": len(self.proxies),
            "active_proxies": len(active_proxies),
            "failed_proxies": len(self.proxies) - len(active_proxies)
        }
