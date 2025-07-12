"""
File Security Module for CodeForge
Validates file operations for security
"""
from pathlib import Path
from typing import Set, Optional
import os
import re


class FileSecurity:
    """
    File operation security validation:
    - Path traversal prevention
    - Filename validation
    - Extension restrictions
    - Size limits
    """
    
    def __init__(self):
        # Dangerous file extensions
        self.blocked_extensions: Set[str] = {
            '.exe', '.dll', '.so', '.dylib', '.app',
            '.bat', '.cmd', '.com', '.scr',
            '.vbs', '.vbe', '.js', '.jse',
            '.ws', '.wsf', '.wsc', '.wsh',
            '.ps1', '.ps1xml', '.ps2', '.ps2xml',
            '.psc1', '.psc2', '.msh', '.msh1', '.msh2',
            '.mshxml', '.msh1xml', '.msh2xml',
            '.scf', '.lnk', '.inf', '.reg',
            '.docm', '.xlsm', '.pptm'  # Macro-enabled Office files
        }
        
        # Blocked filenames
        self.blocked_names: Set[str] = {
            '.htaccess', '.htpasswd', '.env',
            'web.config', 'php.ini', 'wp-config.php',
            '.git', '.svn', '.hg', '.bzr',
            'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
            '.ssh', '.gnupg', '.aws', '.azure',
            '.kube', '.docker', 'Dockerfile',
            '.gitconfig', '.npmrc', '.pypirc'
        }
        
        # Invalid filename patterns
        self.invalid_patterns = [
            re.compile(r'\.\.'),  # Double dots
            re.compile(r'^\.'),   # Hidden files (optional)
            re.compile(r'[\x00-\x1f\x7f]'),  # Control characters
            re.compile(r'[<>:"|?*]'),  # Windows invalid chars
            re.compile(r'^(con|prn|aux|nul|com[0-9]|lpt[0-9])$', re.I),  # Windows reserved
        ]
        
        # Maximum path depth
        self.max_path_depth = 20
        
        # Maximum filename length
        self.max_filename_length = 255
        
    def is_safe_path(self, path: Path, base_path: Path) -> bool:
        """Check if path is safe and within base path"""
        try:
            # Resolve to absolute paths
            abs_path = path.resolve()
            abs_base = base_path.resolve()
            
            # Check if path is within base
            if not str(abs_path).startswith(str(abs_base)):
                return False
                
            # Check path depth
            relative_path = abs_path.relative_to(abs_base)
            if len(relative_path.parts) > self.max_path_depth:
                return False
                
            # Check each component
            for part in relative_path.parts:
                if not self.is_safe_filename(part):
                    return False
                    
            return True
            
        except (ValueError, RuntimeError):
            return False
            
    def is_safe_filename(self, filename: str) -> bool:
        """Check if filename is safe"""
        # Check length
        if len(filename) > self.max_filename_length:
            return False
            
        # Check blocked names
        if filename.lower() in self.blocked_names:
            return False
            
        # Check extensions
        name_lower = filename.lower()
        for ext in self.blocked_extensions:
            if name_lower.endswith(ext):
                return False
                
        # Check patterns
        for pattern in self.invalid_patterns:
            if pattern.search(filename):
                return False
                
        return True
        
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to make it safe"""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Replace invalid characters
        filename = re.sub(r'[<>:"|?*]', '_', filename)
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
        
        # Handle Windows reserved names
        base, ext = os.path.splitext(filename)
        if re.match(r'^(con|prn|aux|nul|com[0-9]|lpt[0-9])$', base, re.I):
            filename = f"_{filename}"
            
        # Truncate if too long
        if len(filename) > self.max_filename_length:
            base, ext = os.path.splitext(filename)
            max_base = self.max_filename_length - len(ext)
            filename = base[:max_base] + ext
            
        return filename
        
    def validate_file_size(self, size: int, max_size: Optional[int] = None) -> bool:
        """Validate file size"""
        if max_size is None:
            max_size = 100 * 1024 * 1024  # 100MB default
            
        return 0 <= size <= max_size
        
    def get_safe_mime_type(self, filename: str) -> Optional[str]:
        """Get MIME type if safe"""
        ext = os.path.splitext(filename)[1].lower()
        
        # Safe MIME types
        mime_map = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.html': 'text/html',
            '.css': 'text/css',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.pdf': 'application/pdf',
            '.zip': 'application/zip',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip'
        }
        
        return mime_map.get(ext)