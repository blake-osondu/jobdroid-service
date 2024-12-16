# tests/test_form_detector.py
import pytest
from src.bot.ml.form_detector import FormDetector

def test_form_field_detection():
    detector = FormDetector()
    
    test_html = """
        <form>
            <input type="text" name="name" required>
            <input type="email" name="email" required>
            <input type="file" name="resume">
        </form>
    """
    
    fields = detector.detect_fields(test_html)
    assert len(fields) >= 3
    assert any(f.field_type == "name" for f in fields)
    assert any(f.field_type == "email" for f in fields)
    assert any(f.field_type == "resume" for f in fields)

def test_required_field_detection():
    detector = FormDetector()
    test_html = """
        <form>
            <input type="text" name="name" required>
            <input type="text" name="optional">
        </form>
    """
    
    fields = detector.detect_fields(test_html)
    required_fields = [f for f in fields if f.required]
    assert len(required_fields) == 1