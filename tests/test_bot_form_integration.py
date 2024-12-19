import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock
sys.path.append(str(Path(__file__).parent.parent / "src"))

from bot.core import JobApplicationBot

async def test_form_processing():
    # Test configuration
    config = {
        'resume_path': 'path/to/resume.pdf',
        'platforms': {
            'linkedin': {'enabled': False},
            'indeed': {'enabled': False}
        }
    }
    
    # Sample job data
    job = {
        'id': 'test123',
        'platform': 'linkedin',
        'company': 'Test Corp',
        'title': 'Python Developer',
        'url': 'https://example.com/job'
    }
    
    # Create bot instance with mocked session
    bot = JobApplicationBot(config)
    
    # Mock the session's get_page_source method
    bot.session = AsyncMock()
    bot.session.get_page_source.return_value = """
        <form action="/apply" method="POST">
            <input type="text" name="full_name" required placeholder="Full Name">
            <input type="email" name="email" required>
            <input type="tel" name="phone" placeholder="Phone Number">
            <input type="file" name="resume" accept=".pdf,.doc,.docx">
            <textarea name="cover_letter" placeholder="Cover Letter"></textarea>
            <button type="submit">Apply</button>
        </form>
    """
    
    # Process job application
    result = await bot._process_job_application(job)
    
    print("\nApplication Result:")
    print(f"Status: {result.status}")
    print(f"Error: {result.error}")
    if result.form_fields:
        print("\nDetected Fields:")
        print(f"Required: {len(result.form_fields['required_fields'])}")
        print(f"Optional: {len(result.form_fields['optional_fields'])}")
        print(f"File Uploads: {len(result.form_fields['file_uploads'])}")
    
    print("\nBot Stats:")
    print(bot.get_stats())

if __name__ == "__main__":
    asyncio.run(test_form_processing()) 