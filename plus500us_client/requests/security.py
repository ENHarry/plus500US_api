"""
Security utility module for credential handling and data protection
"""
from __future__ import annotations
import re
import logging
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class SecureCredentialHandler:
    """Handles credentials with security best practices"""
    
    # Sensitive data patterns to redact from logs
    SENSITIVE_PATTERNS = [
        r'password["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
        r'token["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
        r'secret["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
        r'totp["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
        r'auth["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
        r'sessionId["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
        r'csrfToken["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
        r'bearer\s+([^\s]+)',
        r'basic\s+([^\s]+)',
    ]
    
    # Cookie names that contain sensitive data
    SENSITIVE_COOKIES = {
        'sessionId', 'authToken', 'userId', 'accountId',
        'tradingSession', 'csrfToken', '_auth', 'plus500_session',
        'session_key', 'auth_key', 'access_token', 'refresh_token'
    }
    
    @staticmethod
    def mask_sensitive_data(data: str, mask_char: str = "*") -> str:
        """
        Mask sensitive data in strings for safe logging
        
        Args:
            data: String potentially containing sensitive data
            mask_char: Character to use for masking
            
        Returns:
            String with sensitive data masked
        """
        masked_data = data
        
        for pattern in SecureCredentialHandler.SENSITIVE_PATTERNS:
            def replace_match(match):
                sensitive_value = match.group(1)
                if len(sensitive_value) <= 4:
                    return match.group(0).replace(sensitive_value, mask_char * len(sensitive_value))
                else:
                    # Show first 2 and last 2 characters
                    masked_value = sensitive_value[:2] + mask_char * (len(sensitive_value) - 4) + sensitive_value[-2:]
                    return match.group(0).replace(sensitive_value, masked_value)
            
            masked_data = re.sub(pattern, replace_match, masked_data, flags=re.IGNORECASE)
        
        return masked_data
    
    @staticmethod
    def sanitize_log_data(data: Any) -> Any:
        """
        Sanitize data for safe logging by masking sensitive fields
        
        Args:
            data: Data to sanitize (dict, list, string, etc.)
            
        Returns:
            Sanitized copy of data
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if key.lower() in ['password', 'token', 'secret', 'totp', 'auth']:
                    sanitized[key] = SecureCredentialHandler._mask_value(value)
                elif key in SecureCredentialHandler.SENSITIVE_COOKIES:
                    sanitized[key] = SecureCredentialHandler._mask_value(value)
                else:
                    sanitized[key] = SecureCredentialHandler.sanitize_log_data(value)
            return sanitized
            
        elif isinstance(data, list):
            return [SecureCredentialHandler.sanitize_log_data(item) for item in data]
            
        elif isinstance(data, str):
            return SecureCredentialHandler.mask_sensitive_data(data)
            
        else:
            return data
    
    @staticmethod
    def _mask_value(value: str) -> str:
        """Mask a single value"""
        if not value or not isinstance(value, str):
            return value
        
        if len(value) <= 4:
            return "*" * len(value)
        else:
            return value[:2] + "*" * (len(value) - 4) + value[-2:]
    
    @staticmethod
    def secure_session_backup(session_data: Dict[str, Any], backup_path: str) -> bool:
        """
        Create secure session backup with sensitive data protection
        
        Args:
            session_data: Session data to backup
            backup_path: Path for backup file
            
        Returns:
            True if backup was successful
        """
        try:
            # Create sanitized copy for backup
            backup_data = {
                'cookies': [],
                'headers': {},
                'timestamp': session_data.get('timestamp'),
                'account_type': session_data.get('account_type'),
                'checksum': None
            }
            
            # Backup cookies with selective masking
            for cookie in session_data.get('cookies', []):
                cookie_backup = {
                    'name': cookie.get('name'),
                    'domain': cookie.get('domain'),
                    'path': cookie.get('path'),
                    'secure': cookie.get('secure'),
                    'httpOnly': cookie.get('httpOnly')
                }
                
                # Only include value for essential cookies, mask others
                if cookie.get('name') in SecureCredentialHandler.SENSITIVE_COOKIES:
                    cookie_backup['value'] = cookie.get('value')  # Store actual value for essential cookies
                    cookie_backup['_sensitive'] = True
                else:
                    cookie_backup['value'] = SecureCredentialHandler._mask_value(cookie.get('value', ''))
                    cookie_backup['_sensitive'] = False
                
                backup_data['cookies'].append(cookie_backup)
            
            # Backup headers (mask authorization headers)
            for header, value in session_data.get('headers', {}).items():
                if header.lower() in ['authorization', 'x-csrf-token', 'x-auth-token']:
                    backup_data['headers'][header] = SecureCredentialHandler._mask_value(value)
                else:
                    backup_data['headers'][header] = value
            
            # Generate checksum for integrity verification
            backup_json = json.dumps(backup_data, sort_keys=True)
            backup_data['checksum'] = hashlib.sha256(backup_json.encode()).hexdigest()[:16]
            
            # Write to file with restricted permissions
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            # Set restrictive file permissions (owner read/write only)
            try:
                backup_file.chmod(0o600)
            except OSError:
                logger.warning("Could not set restrictive permissions on backup file")
            
            logger.info(f"Secure session backup created: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create secure session backup: {e}")
            return False
    
    @staticmethod
    def validate_session_backup(backup_path: str) -> Dict[str, Any]:
        """
        Validate and load session backup with integrity checking
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Dictionary with validation results and data
        """
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            # Verify checksum if present
            stored_checksum = backup_data.pop('checksum', None)
            if stored_checksum:
                current_json = json.dumps(backup_data, sort_keys=True)
                current_checksum = hashlib.sha256(current_json.encode()).hexdigest()[:16]
                
                if stored_checksum != current_checksum:
                    logger.warning(f"Checksum mismatch in backup file: {backup_path}")
                    return {
                        'valid': False,
                        'error': 'Integrity check failed',
                        'data': None
                    }
            
            return {
                'valid': True,
                'data': backup_data,
                'sensitive_cookies': sum(1 for cookie in backup_data.get('cookies', []) 
                                       if cookie.get('_sensitive'))
            }
            
        except Exception as e:
            logger.error(f"Failed to validate session backup: {e}")
            return {
                'valid': False,
                'error': str(e),
                'data': None
            }

class SecurityAuditor:
    """Performs security audits on credential handling"""
    
    @staticmethod
    def audit_log_files(log_directory: str) -> Dict[str, Any]:
        """
        Audit log files for exposed sensitive data
        
        Args:
            log_directory: Directory containing log files
            
        Returns:
            Audit results
        """
        results = {
            'files_scanned': 0,
            'issues_found': [],
            'recommendations': []
        }
        
        log_dir = Path(log_directory)
        if not log_dir.exists():
            return results
        
        for log_file in log_dir.glob("*.log"):
            results['files_scanned'] += 1
            
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                
                # Check for exposed passwords
                if re.search(r'password["\']?\s*[:=]\s*["\']?[^*][^"\'}\s,]{3,}', content, re.IGNORECASE):
                    results['issues_found'].append({
                        'file': str(log_file),
                        'issue': 'Potential password exposure in logs',
                        'severity': 'HIGH'
                    })
                
                # Check for exposed tokens
                if re.search(r'token["\']?\s*[:=]\s*["\']?[^*][^"\'}\s,]{10,}', content, re.IGNORECASE):
                    results['issues_found'].append({
                        'file': str(log_file),
                        'issue': 'Potential token exposure in logs',
                        'severity': 'HIGH'
                    })
                
                # Check for session IDs
                if re.search(r'sessionId["\']?\s*[:=]\s*["\']?[^*][^"\'}\s,]{10,}', content, re.IGNORECASE):
                    results['issues_found'].append({
                        'file': str(log_file),
                        'issue': 'Potential session ID exposure in logs',
                        'severity': 'MEDIUM'
                    })
                    
            except Exception as e:
                results['issues_found'].append({
                    'file': str(log_file),
                    'issue': f'Could not scan file: {e}',
                    'severity': 'LOW'
                })
        
        # Generate recommendations
        if any(issue['severity'] == 'HIGH' for issue in results['issues_found']):
            results['recommendations'].extend([
                'Implement credential masking in all log statements',
                'Review logging configuration to exclude sensitive data',
                'Consider using structured logging with field-level filtering'
            ])
        
        return results
    
    @staticmethod
    def audit_session_backups(backup_directory: str) -> Dict[str, Any]:
        """
        Audit session backup files for security issues
        
        Args:
            backup_directory: Directory containing backup files
            
        Returns:
            Audit results
        """
        results = {
            'backups_scanned': 0,
            'security_issues': [],
            'recommendations': []
        }
        
        backup_dir = Path(backup_directory)
        if not backup_dir.exists():
            return results
        
        for backup_file in backup_dir.glob("*.json"):
            results['backups_scanned'] += 1
            
            try:
                # Check file permissions
                file_mode = backup_file.stat().st_mode & 0o777
                if file_mode != 0o600:
                    results['security_issues'].append({
                        'file': str(backup_file),
                        'issue': f'Insecure file permissions: {oct(file_mode)}',
                        'severity': 'MEDIUM'
                    })
                
                # Validate backup integrity
                validation = SecureCredentialHandler.validate_session_backup(str(backup_file))
                if not validation['valid']:
                    results['security_issues'].append({
                        'file': str(backup_file),
                        'issue': f'Backup integrity check failed: {validation["error"]}',
                        'severity': 'HIGH'
                    })
                
            except Exception as e:
                results['security_issues'].append({
                    'file': str(backup_file),
                    'issue': f'Could not audit backup: {e}',
                    'severity': 'LOW'
                })
        
        # Generate recommendations
        if results['security_issues']:
            results['recommendations'].extend([
                'Set restrictive permissions (600) on all backup files',
                'Implement backup encryption for sensitive session data',
                'Regular cleanup of old backup files',
                'Consider using system keyring for session data storage'
            ])
        
        return results

def secure_logger(name: str) -> logging.Logger:
    """
    Create a logger with automatic sensitive data filtering
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger with security filtering
    """
    logger = logging.getLogger(name)
    
    # Add custom filter to mask sensitive data
    class SensitiveDataFilter(logging.Filter):
        def filter(self, record):
            if hasattr(record, 'msg') and isinstance(record.msg, str):
                record.msg = SecureCredentialHandler.mask_sensitive_data(record.msg)
            
            if hasattr(record, 'args') and record.args:
                # Sanitize string arguments
                sanitized_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        sanitized_args.append(SecureCredentialHandler.mask_sensitive_data(arg))
                    elif isinstance(arg, (dict, list)):
                        sanitized_args.append(SecureCredentialHandler.sanitize_log_data(arg))
                    else:
                        sanitized_args.append(arg)
                record.args = tuple(sanitized_args)
            
            return True
    
    logger.addFilter(SensitiveDataFilter())
    return logger
