import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock
sys.path.append(str(Path(__file__).parent.parent / "src"))

from bot.automation.form_filler import FormFiller, FormField

async def test_form_filling():
    # Mock Selenium WebDriver
    mock_driver = Mock()
    mock_element = Mock()
    mock_driver.find_element.return_value = mock_element
    
    # Test user data
    user_data = {
        'full_name': 'John Doe',
        'email': 'john.doe@example.com',
        'phone': '123-456-7890',
        'years_of_experience': '5',
        'education_level': "Bachelor's Degree",
        'resume_path': '/path/to/resume.pdf',
        'preferred_work_type': ['remote', 'hybrid'],
        'willing_to_relocate': True,
        'skills': ['Python', 'JavaScript', 'SQL'],
        'cover_letter_text': 'I am excited to apply...',
        'available_start_date': '2024-04-01'
    }
    
    # Create form filler
    form_filler = FormFiller(mock_driver, user_data)
    
    # Test fields with various types
    test_fields = [
        FormField('full_name', 'input', True, purpose='name'),
        FormField('email', 'input', True, purpose='email'),
        FormField('phone', 'input', False, purpose='phone'),
        FormField('resume', 'file', True, value=user_data['resume_path']),
        FormField('work_type', 'multi-select', True, purpose='work_type'),
        FormField('relocation', 'checkbox', False, purpose='relocation'),
        FormField('skills', 'multi-select', True, purpose='skills'),
        FormField('cover_letter', 'rich-text', True, purpose='cover_letter'),
        FormField('start_date', 'date', True, purpose='start_date'),
        FormField('salary_range', 'range', False, value='75000')
    ]
    
    # Fill form
    success = await form_filler.fill_form(test_fields)
    
    print(f"\nForm filling {'successful' if success else 'failed'}")
    
    # Verify interactions
    expected_calls = len(test_fields)
    actual_calls = mock_driver.find_element.call_count
    print(f"Expected element lookups: {expected_calls}")
    print(f"Actual element lookups: {actual_calls}")

if __name__ == "__main__":
    asyncio.run(test_form_filling())