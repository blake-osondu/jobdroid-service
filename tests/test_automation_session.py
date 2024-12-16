# tests/test_automation_session.py
import pytest
from src.bot.automation.session import AutomationSession

@pytest.mark.asyncio
async def test_session_initialization(config):
    session = AutomationSession(config)
    initialized = await session.initialize()
    assert initialized is True
    assert session.driver is not None

@pytest.mark.asyncio
async def test_form_filling(config):
    session = AutomationSession(config)
    await session.initialize()
    
    test_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "resume": "path/to/resume.pdf"
    }
    
    result = await session.fill_application_form(test_data)
    assert result is True

@pytest.mark.asyncio
async def test_error_handling(config):
    session = AutomationSession(config)
    await session.initialize()
    
    # Test invalid form data
    with pytest.raises(ValueError):
        await session.fill_application_form({})