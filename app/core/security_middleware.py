"""
Security middleware for injection protection
"""
import re
from typing import Any, Dict, List, Union
from fastapi import HTTPException, status
from bson import ObjectId


class InjectionProtection:
    """Protection against SQL/NoSQL injection attacks"""
    
    # Dangerous MongoDB operators that should not be in user input
    DANGEROUS_OPERATORS = [
        '$where', '$regex', '$expr', '$jsonSchema', '$text',
        '$elemMatch', '$gt', '$gte', '$lt', '$lte', '$ne',
        '$in', '$nin', '$exists', '$type', '$mod', '$all',
        '$size', '$not', '$and', '$or', '$nor'
    ]
    
    # Dangerous characters for injection
    DANGEROUS_CHARS = [
        ';', '--', '/*', '*/', 'xp_', 'sp_', 'DROP', 'DELETE',
        'INSERT', 'UPDATE', 'UNION', 'SELECT', 'EXEC', 'ALTER'
    ]
    
    @staticmethod
    def sanitize_input(input_value: Any) -> Any:
        """Sanitize input to prevent injection attacks"""
        if input_value is None:
            return None
            
        if isinstance(input_value, str):
            return InjectionProtection._sanitize_string(input_value)
        elif isinstance(input_value, dict):
            return InjectionProtection._sanitize_dict(input_value)
        elif isinstance(input_value, list):
            return [InjectionProtection.sanitize_input(item) for item in input_value]
        else:
            return input_value
    
    @staticmethod
    def _sanitize_string(text: str) -> str:
        """Sanitize string input"""
        # Remove dangerous characters
        for char in InjectionProtection.DANGEROUS_CHARS:
            text = text.replace(char, '')
        
        # Check for dangerous operators
        for operator in InjectionProtection.DANGEROUS_OPERATORS:
            if operator in text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dangerous operator {operator} detected in input"
                )
        
        # Limit string length to prevent DoS
        if len(text) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input too long"
            )
        
        return text.strip()
    
    @staticmethod
    def _sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary input"""
        sanitized = {}
        for key, value in data.items():
            # Check for dangerous operators in keys
            if key.startswith('$'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dangerous operator {key} detected in input"
                )
            
            sanitized_key = InjectionProtection._sanitize_string(key)
            sanitized_value = InjectionProtection.sanitize_input(value)
            sanitized[sanitized_key] = sanitized_value
        
        return sanitized
    
    @staticmethod
    def validate_object_id(object_id: str) -> bool:
        """Validate MongoDB ObjectId format"""
        try:
            ObjectId(object_id)
            return True
        except:
            return False
    
    @staticmethod
    def sanitize_regex_pattern(pattern: str) -> str:
        """Sanitize regex patterns for safe usage"""
        # Escape special regex characters
        escaped = re.escape(pattern)
        
        # Remove dangerous regex constructs
        dangerous_patterns = [
            r'\\[eE]',  # \e escape sequence
            r'\\[xX][0-9a-fA-F]{2}',  # Hex escape
            r'\\[0-7]{1,3}',  # Octal escape
            r'\(\?[^)]*\)',  # Regex flags and options
            r'\(\?[=!]',  # Lookahead assertions
            r'\(\?<!',  # Negative lookahead
            r'\(\?=',  # Positive lookahead
            r'\(\?!',  # Negative lookahead
        ]
        
        for dangerous in dangerous_patterns:
            escaped = re.sub(dangerous, '', escaped)
        
        return escaped
    
    @staticmethod
    def _has_sequential_chars(password: str) -> bool:
        """Check for sequential characters in password"""
        password_lower = password.lower()
        
        # Check for numeric sequences (1234, 2345, etc.)
        for i in range(len(password_lower) - 3):
            if (password_lower[i:i+4].isdigit() and
                int(password_lower[i+1]) == int(password_lower[i]) + 1 and
                int(password_lower[i+2]) == int(password_lower[i]) + 2 and
                int(password_lower[i+3]) == int(password_lower[i]) + 3):
                return True
        
        # Check for alphabetic sequences (abcd, bcde, etc.)
        for i in range(len(password_lower) - 3):
            if (password_lower[i:i+4].isalpha() and
                ord(password_lower[i+1]) == ord(password_lower[i]) + 1 and
                ord(password_lower[i+2]) == ord(password_lower[i]) + 2 and
                ord(password_lower[i+3]) == ord(password_lower[i]) + 3):
                return True
        
        return False
    
    @staticmethod
    def _has_repeated_chars(password: str) -> bool:
        """Check for repeated characters in password"""
        for i in range(len(password) - 3):
            if (password[i] == password[i+1] == password[i+2] == password[i+3]):
                return True
        return False
    
    @staticmethod
    def _calculate_password_score(password: str) -> int:
        """Calculate password strength score (1-5)"""
        score = 0
        
        # Length scoring
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        
        # Character variety scoring
        if re.search(r'[A-Z]', password):
            score += 1
        if re.search(r'[a-z]', password):
            score += 0.5
        if re.search(r'\d', password):
            score += 0.5
        if re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]', password):
            score += 1
        
        return min(int(score), 5)
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Validate password strength with comprehensive requirements"""
        
        # Length requirements
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must not exceed 128 characters"
        
        # Character requirements
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter (A-Z)"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter (a-z)"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit (0-9)"
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]', password):
            return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}:\"|,.<>/? )"
        
        # Enhanced password blacklist with real leaked passwords
        common_passwords = {
            # Top 10 most common passwords (from breach data)
            '123456', 'password', '123456789', '12345678', '12345', '1234567', 
            '1234567890', '1234', 'qwerty', 'abc123',
            
            # Common variations
            'password1', 'password123', 'password123!', 'admin', 'admin123', 'admin123!',
            'letmein', 'letmein123', 'welcome', 'welcome123', 'welcome123!',
            'changeme', 'changeme123', 'default', 'default123', 'root', 'root123',
            
            # Year-based passwords
            'password2023', 'password2024', 'password2025', 'admin2023', 'admin2024',
            'welcome2023', 'welcome2024', '1234562023', '1234562024',
            
            # Keyboard patterns
            'qwerty', 'qwerty123', 'qwerty123!', 'asdf', 'asdf123', 'zxcv', 'zxcv123',
            '123qwe', 'qwe123', '1q2w3e', '1qaz2wsx',
            
            # Common names and words
            'dragon', 'master', 'superman', 'princess', 'football', 'baseball',
            'shadow', 'monkey', 'michael', 'jennifer', 'thomas', 'jordan',
            
            # Tech-related passwords
            'computer', 'internet', 'server', 'database', 'network', 'system',
            'oracle', 'mysql', 'passwd', 'passw0rd', 'p@ssword', 'p@ssw0rd',
            
            # Business-related
            'company', 'office', 'business', 'corporate', 'manager', 'employee',
            'retail', 'store', 'shop', 'sales', 'service', 'customer',
            
            # Simple numeric patterns
            '111111', '222222', '333333', '444444', '555555', '666666',
            '777777', '888888', '999999', '000000', '123123', '321321',
            
            # Leaked passwords from major breaches
            'starwars', 'harley', 'batman', 'superman', 'ironman', 'spiderman',
            'pokemon', 'mario', 'zelda', 'halo', 'call of duty', 'fortnite',
            
            # Common phrases
            'iloveyou', 'trustno1', 'whatever', 'nothing', 'blink182',
            
            # Security-related (ironically common)
            'security', 'secure', 'protected', 'private', 'secret', 'confidential'
        }
        
        if password.lower() in common_passwords:
            return False, "Password is too common. Please choose a more secure password"
        
        # Check for sequential characters
        if InjectionProtection._has_sequential_chars(password):
            return False, "Password cannot contain sequential characters (e.g., '1234', 'abcd')"
        
        # Check for repeated characters
        if InjectionProtection._has_repeated_chars(password):
            return False, "Password cannot contain repeated characters (e.g., 'aaaa', '1111')"
        
        # Calculate password strength score
        score = InjectionProtection._calculate_password_score(password)
        
        if score < 3:
            return False, "Password is too weak. Please include a mix of different character types"
        
        return True, "Password meets all security requirements"


# Global instance for easy access
injection_protection = InjectionProtection()
