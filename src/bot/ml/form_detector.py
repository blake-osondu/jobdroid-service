from typing import Dict, List, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup

@dataclass
class FormField:
    """Represents a form field with its attributes"""
    name: str
    field_type: str
    required: bool
    attributes: Dict[str, str]

class FormDetector:
    def __init__(self):
        self.common_field_patterns = {
            'name': ['name', 'full[_-]?name', 'first[_-]?name', 'last[_-]?name'],
            'email': ['email', 'e[_-]?mail'],
            'phone': ['phone', 'telephone', 'mobile', 'cell'],
            'resume': ['resume', 'cv', 'upload', 'document'],
            'cover_letter': ['cover[_-]?letter', 'letter', 'introduction'],
            'experience': ['experience', 'years[_-]?of[_-]?experience'],
            'education': ['education', 'degree', 'qualification']
        }

    async def detect_fields(self, page_source: str) -> Dict[str, List[FormField]]:
        """Detect form fields in the page"""
        soup = BeautifulSoup(page_source, 'html.parser')
        
        forms = soup.find_all('form')
        detected_fields = []
        
        for form in forms:
            fields = {
                'inputs': form.find_all('input'),
                'textareas': form.find_all('textarea'),
                'selects': form.find_all('select'),
                'file_uploads': form.find_all('input', type='file')
            }
            
            detected_fields.append(self._analyze_form_fields(fields))
        
        return detected_fields

    def _analyze_form_fields(self, fields: Dict) -> Dict[str, List[FormField]]:
        """Analyze form fields and identify their likely purpose"""
        analyzed = {
            'required_fields': [],
            'optional_fields': [],
            'file_uploads': [],
            'unknown_fields': []
        }
        
        # Process each field type
        for field_type, elements in fields.items():
            for element in elements:
                field_info = self._identify_field_purpose(element)
                if field_info:
                    field = FormField(
                        name=element.get('name', ''),
                        field_type=element.name,
                        required=bool(element.get('required')),
                        attributes=field_info['attributes']
                    )
                    
                    if element.get('required'):
                        analyzed['required_fields'].append(field)
                    else:
                        analyzed['optional_fields'].append(field)
                else:
                    analyzed['unknown_fields'].append(FormField(
                        name=element.get('name', ''),
                        field_type=element.name,
                        required=bool(element.get('required')),
                        attributes={
                            'name': element.get('name', ''),
                            'id': element.get('id', ''),
                            'class': ' '.join(element.get('class', []))
                        }
                    ))
        
        return analyzed

    def _identify_field_purpose(self, element) -> Optional[Dict]:
        """Identify the likely purpose of a form field"""
        field_attrs = {
            'name': element.get('name', ''),
            'id': element.get('id', ''),
            'class': ' '.join(element.get('class', [])),
            'placeholder': element.get('placeholder', '')
        }
        
        # Combine all text attributes for matching
        text_to_match = ' '.join(field_attrs.values()).lower()
        
        # Match against known patterns
        for purpose, patterns in self.common_field_patterns.items():
            if any(pattern in text_to_match for pattern in patterns):
                return {
                    'purpose': purpose,
                    'element_type': element.name,
                    'attributes': field_attrs
                }
        
        return None
