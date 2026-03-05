"""
Input validation utilities for robust request handling.
"""

import re
import logging
from typing import Any, Optional, List, Dict, Callable

from services.exceptions import ValidationError

logger = logging.getLogger(__name__)


class Validator:
    """Helper class for input validation."""
    
    @staticmethod
    def validate_string(
        value: Any,
        field_name: str,
        min_length: int = 1,
        max_length: int = 10000,
        required: bool = True,
    ) -> str:
        """Validate string input."""
        if required and (value is None or value == ""):
            raise ValidationError(
                f"Feld '{field_name}' ist erforderlich",
                details={"field": field_name, "reason": "required"},
            )
        
        if value is None or value == "":
            return "" if not required else ""
        
        if not isinstance(value, str):
            raise ValidationError(
                f"Feld '{field_name}' muss ein String sein",
                details={"field": field_name, "type": type(value).__name__},
            )
        
        value = value.strip()
        
        if len(value) < min_length:
            raise ValidationError(
                f"Feld '{field_name}' ist zu kurz (min: {min_length})",
                details={"field": field_name, "length": len(value)},
            )
        
        if len(value) > max_length:
            raise ValidationError(
                f"Feld '{field_name}' ist zu lang (max: {max_length})",
                details={"field": field_name, "length": len(value)},
            )
        
        return value
    
    @staticmethod
    def validate_file_id(file_id: str) -> str:
        """Validate file_id format (UUID-like)."""
        if not file_id or not isinstance(file_id, str):
            raise ValidationError("file_id ist erforderlich")
        
        file_id = file_id.strip()
        
        # Allow alphanumeric, hyphens (for UUIDs)
        if not re.match(r'^[a-zA-Z0-9\-]{1,64}$', file_id):
            raise ValidationError("file_id hat ungültiges Format")
        
        return file_id
    
    @staticmethod
    def validate_dict(
        value: Any,
        field_name: str,
        required: bool = True,
    ) -> Dict:
        """Validate dictionary input."""
        if required and (value is None or value == {}):
            raise ValidationError(
                f"Feld '{field_name}' ist erforderlich",
                details={"field": field_name},
            )
        
        if value is None:
            return {} if not required else {}
        
        if not isinstance(value, dict):
            raise ValidationError(
                f"Feld '{field_name}' muss ein Objekt sein",
                details={"field": field_name, "type": type(value).__name__},
            )
        
        return value
    
    @staticmethod
    def validate_list(
        value: Any,
        field_name: str,
        required: bool = True,
    ) -> List:
        """Validate list input."""
        if required and (value is None or value == []):
            raise ValidationError(
                f"Feld '{field_name}' ist erforderlich",
                details={"field": field_name},
            )
        
        if value is None:
            return [] if not required else []
        
        if not isinstance(value, list):
            raise ValidationError(
                f"Feld '{field_name}' muss eine Liste sein",
                details={"field": field_name, "type": type(value).__name__},
            )
        
        return value
    
    @staticmethod
    def validate_number(
        value: Any,
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = True,
    ) -> int:
        """Validate numeric input."""
        if required and value is None:
            raise ValidationError(
                f"Feld '{field_name}' ist erforderlich",
                details={"field": field_name},
            )
        
        if value is None:
            return 0 if not required else 0
        
        try:
            num = int(value)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Feld '{field_name}' muss eine Zahl sein",
                details={"field": field_name, "value": str(value)},
            )
        
        if min_value is not None and num < min_value:
            raise ValidationError(
                f"Feld '{field_name}' muss >= {min_value} sein",
                details={"field": field_name, "value": num, "min": min_value},
            )
        
        if max_value is not None and num > max_value:
            raise ValidationError(
                f"Feld '{field_name}' muss <= {max_value} sein",
                details={"field": field_name, "value": num, "max": max_value},
            )
        
        return num
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove potentially dangerous characters from filename."""
        # Remove path traversal attempts
        filename = filename.replace("../", "").replace("..\\", "")
        filename = filename.replace("/", "_").replace("\\", "_")
        
        # Keep only safe characters
        filename = re.sub(r'[^\w\s\-\.\(\),]', '', filename)
        filename = re.sub(r'[\s]+', '_', filename)
        
        # Prevent empty filenames
        if not filename or filename.startswith('.'):
            filename = "file"
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        
        return filename
