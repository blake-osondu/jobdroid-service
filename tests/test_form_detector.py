# tests/test_form_detector.py
import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from bot.ml.form_detector import FormDetector

async def test_form_detection():
    # Sample HTML form
    sample_form = """
    <form action="/apply" method="POST">
        <input type="text" name="full_name" required placeholder="Full Name">
        <input type="email" name="email" required>
        <input type="tel" name="phone" placeholder="Phone Number">
        <input type="file" name="resume" accept=".pdf,.doc,.docx">
        <textarea name="cover_letter" placeholder="Cover Letter"></textarea>
        <select name="experience">
            <option value="1-3">1-3 years</option>
            <option value="3-5">3-5 years</option>
            <option value="5+">5+ years</option>
        </select>
        <button type="submit">Apply</button>
    </form>
    """
    
    detector = FormDetector()
    fields = await detector.detect_fields(sample_form)
    
    print("Detected Fields:")
    for form in fields:
        print("\nRequired Fields:", form['required_fields'])
        print("Optional Fields:", form['optional_fields'])
        print("File Uploads:", form['file_uploads'])
        print("Unknown Fields:", form['unknown_fields'])

if __name__ == "__main__":
    asyncio.run(test_form_detection())