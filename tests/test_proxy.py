# tests/test_proxy.py
import pytest
import asyncio
from src.utils.proxy import ProxyRotator, Proxy

@pytest.mark.asyncio
async def test_proxy_rotation():
    rotator = ProxyRotator()
    # Test proxy data
    test_proxies = [
        {"host": "proxy1.test.com", "port": 8080},
        {"host": "proxy2.test.com", "port": 8080},
        {"host": "proxy3.test.com", "port": 8080}
    ]
    
    # Load test proxies
    for proxy_data in test_proxies:
        rotator.proxies.append(Proxy(**proxy_data))
    
    # Test rotation
    first_proxy = await rotator.get_working_proxy()
    assert first_proxy is not None
    assert first_proxy.host == "proxy1.test.com"
    
    # Test failed proxy handling
    rotator.mark_proxy_failed(first_proxy)
    next_proxy = await rotator.get_working_proxy()
    assert next_proxy.host == "proxy2.test.com"

@pytest.mark.asyncio
async def test_proxy_testing():
    rotator = ProxyRotator()
    test_proxy = Proxy(host="test.proxy.com", port=8080)
    
    # Test proxy testing functionality
    result = await rotator.test_proxy(test_proxy)
    assert isinstance(result, bool)

@pytest.mark.asyncio
async def test_proxy_stats():
    rotator = ProxyRotator()
    # Add test proxies
    rotator.proxies = [
        Proxy(host=f"proxy{i}.test.com", port=8080)
        for i in range(3)
    ]
    
    stats = rotator.get_stats()
    assert stats["total_proxies"] == 3
    assert "active_proxies" in stats