# src/bot/automation/form_filler.py
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
from selenium.webdriver.common.keys import Keys

@dataclass
class FormField:
    identifier: str  # name or id of the field
    field_type: str  # input, textarea, select, radio, checkbox, etc.
    required: bool
    value: Optional[Union[str, List[str]]] = None  # Allow list for multi-select
    purpose: Optional[str] = None  # name, email, phone, etc.
    options: Optional[List[str]] = None  # For radio, checkbox, select options

class FormFiller:
    def __init__(self, driver, user_data: Dict):
        """Initialize form filler with user data"""
        self.driver = driver
        self.user_data = user_data
        self.logger = logging.getLogger(__name__)
        self.timeout = 10  # seconds to wait for elements
        
        # Extend field mapping for new field types
        self.field_mapping = {
            # Basic fields
            'name': user_data.get('full_name'),
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name'),
            'email': user_data.get('email'),
            'phone': user_data.get('phone'),
            
            # Professional details
            'experience': user_data.get('years_of_experience'),
            'education': user_data.get('education_level'),
            'linkedin': user_data.get('linkedin_url'),
            'github': user_data.get('github_url'),
            'website': user_data.get('portfolio_url'),
            
            # Employment
            'current_company': user_data.get('current_company'),
            'current_position': user_data.get('current_position'),
            'desired_salary': user_data.get('desired_salary'),
            
            # Preferences
            'work_type': user_data.get('preferred_work_type', []),  # remote, hybrid, onsite
            'relocation': user_data.get('willing_to_relocate', False),
            'visa_sponsorship': user_data.get('needs_visa_sponsorship', False),
            'start_date': user_data.get('available_start_date'),
            
            # Skills and technologies
            'skills': user_data.get('skills', []),
            'languages': user_data.get('languages', []),
            
            # Additional information
            'cover_letter': user_data.get('cover_letter_text'),
            'references': user_data.get('references', False),
            'security_clearance': user_data.get('has_security_clearance', False)
        }

    async def fill_form(self, fields: List[FormField]) -> bool:
        """Fill all form fields"""
        try:
            for field in fields:
                if not await self._fill_field(field):
                    if field.required:
                        self.logger.error(f"Failed to fill required field: {field.identifier}")
                        return False
                    else:
                        self.logger.warning(f"Skipped optional field: {field.identifier}")
            return True
            
        except Exception as e:
            self.logger.error(f"Form filling failed: {e}")
            return False

    async def _fill_field(self, field: FormField) -> bool:
        """Fill a single form field based on its type"""
        try:
            # Find the element
            element = await self._find_element(field.identifier)
            if not element:
                return False

            # Get the value to fill
            value = field.value or self._get_field_value(field)
            if not value and field.required:
                self.logger.error(f"No value found for required field: {field.identifier}")
                return False

            # Fill based on field type
            fill_methods = {
                'select': self._fill_select,
                'multi-select': self._fill_multi_select,
                'file': self._upload_file,
                'textarea': self._fill_textarea,
                'radio': self._fill_radio,
                'checkbox': self._fill_checkbox,
                'rich-text': self._fill_rich_text,
                'date': self._fill_date,
                'range': self._fill_range
            }

            fill_method = fill_methods.get(field.field_type, self._fill_input)
            return await fill_method(element, value)

        except Exception as e:
            self.logger.error(f"Failed to fill field {field.identifier}: {e}")
            return False

    def _get_field_value(self, field: FormField) -> Optional[str]:
        """Get the appropriate value for a field based on its purpose"""
        if field.purpose:
            return self.field_mapping.get(field.purpose)
        return None

    async def _find_element(self, identifier: str):
        """Find element by name or ID"""
        try:
            # Try by ID first
            element = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.ID, identifier))
            )
            return element
        except TimeoutException:
            try:
                # Try by name
                element = WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.NAME, identifier))
                )
                return element
            except TimeoutException:
                self.logger.error(f"Element not found: {identifier}")
                return None

    async def _fill_input(self, element, value: str) -> bool:
        """Fill a regular input field"""
        try:
            element.clear()
            element.send_keys(value)
            return True
        except ElementNotInteractableException:
            self.logger.error(f"Element not interactable")
            return False

    async def _fill_select(self, element, value: str) -> bool:
        """Fill a select dropdown"""
        try:
            # Try exact match first
            for option in element.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == value or option.text == value:
                    option.click()
                    return True
            
            # Try partial match if exact match fails
            for option in element.find_elements(By.TAG_NAME, "option"):
                if value.lower() in option.text.lower():
                    option.click()
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to fill select: {e}")
            return False

    async def _fill_textarea(self, element, value: str) -> bool:
        """Fill a textarea field"""
        try:
            element.clear()
            element.send_keys(value)
            return True
        except Exception as e:
            self.logger.error(f"Failed to fill textarea: {e}")
            return False

    async def _upload_file(self, element, file_path: str) -> bool:
        """Upload a file"""
        try:
            element.send_keys(file_path)
            return True
        except Exception as e:
            self.logger.error(f"Failed to upload file: {e}")
            return False

    async def submit_form(self) -> bool:
        """Submit the form"""
        try:
            # Try to find submit button by type
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 
                "button[type='submit'], input[type='submit']")
            submit_button.click()
            return True
        except Exception as e:
            self.logger.error(f"Failed to submit form: {e}")
            return False

    async def _fill_multi_select(self, element, values: List[str]) -> bool:
        """Fill a multi-select dropdown"""
        try:
            select = Select(element)
            if not select.is_multiple:
                self.logger.error("Field is not a multi-select")
                return False
            
            select.deselect_all()
            selected_any = False
            
            for value in values:
                # Try exact match first
                for option in select.options:
                    if option.get_attribute("value") == value or option.text == value:
                        option.click()
                        selected_any = True
                        break
                
                # Try partial match if exact match fails
                if not selected_any:
                    for option in select.options:
                        if value.lower() in option.text.lower():
                            option.click()
                            selected_any = True
                            break
            
            return selected_any
            
        except Exception as e:
            self.logger.error(f"Failed to fill multi-select: {e}")
            return False

    async def _fill_radio(self, element, value: str) -> bool:
        """Fill a radio button group"""
        try:
            # Find all radio buttons in the group
            name = element.get_attribute("name")
            radio_group = self.driver.find_elements(By.NAME, name)
            
            for radio in radio_group:
                radio_value = radio.get_attribute("value")
                if radio_value == value or radio.get_attribute("label") == value:
                    if not radio.is_selected():
                        radio.click()
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to fill radio button: {e}")
            return False

    async def _fill_checkbox(self, element, value: bool) -> bool:
        """Fill a checkbox"""
        try:
            is_checked = element.is_selected()
            
            if value and not is_checked:
                element.click()
            elif not value and is_checked:
                element.click()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to fill checkbox: {e}")
            return False

    async def _fill_rich_text(self, element, value: str) -> bool:
        """Fill a rich text editor"""
        try:
            # Try different approaches for rich text editors
            
            # 1. Try standard input if it's a contenteditable div
            if element.get_attribute("contenteditable") == "true":
                element.clear()
                element.send_keys(value)
                return True
            
            # 2. Try iframe-based editors
            try:
                # Switch to iframe if present
                iframe = element.find_element(By.TAG_NAME, "iframe")
                self.driver.switch_to.frame(iframe)
                
                # Find and fill the editor body
                editor_body = self.driver.find_element(By.CSS_SELECTOR, "body")
                editor_body.clear()
                editor_body.send_keys(value)
                
                # Switch back to default content
                self.driver.switch_to.default_content()
                return True
                
            except Exception:
                pass
            
            # 3. Fall back to regular input
            return await self._fill_input(element, value)
            
        except Exception as e:
            self.logger.error(f"Failed to fill rich text editor: {e}")
            return False

    async def _fill_date(self, element, value: str) -> bool:
        """Fill a date input"""
        try:
            # Clear any existing value
            element.clear()
            
            # Try to set value directly
            element.send_keys(value)
            
            # If direct input fails, try JavaScript
            if not element.get_attribute("value"):
                self.driver.execute_script(
                    "arguments[0].value = arguments[1]", 
                    element, 
                    value
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to fill date: {e}")
            return False

    async def _fill_range(self, element, value: str) -> bool:
        """Fill a range/slider input"""
        try:
            # Convert value to number
            num_value = float(value)
            
            # Get min/max values
            min_value = float(element.get_attribute("min") or 0)
            max_value = float(element.get_attribute("max") or 100)
            
            # Validate value is within range
            if num_value < min_value or num_value > max_value:
                self.logger.error(f"Value {value} is outside range [{min_value}, {max_value}]")
                return False
            
            # Set value using JavaScript
            self.driver.execute_script(
                "arguments[0].value = arguments[1]", 
                element, 
                str(num_value)
            )
            
            # Trigger change event
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('change'))", 
                element
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to fill range: {e}")
            return False