"""
Cryptographic utilities for secure data handling
"""
from cryptography.fernet import Fernet
from typing import Optional
import os
import base64

# Get encryption key from environment or generate one
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # In production, this should always come from environment
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    
# Initialize Fernet cipher
cipher_suite = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


def encrypt_string(plaintext: str) -> str:
    """
    Encrypt a string using Fernet symmetric encryption
    
    Args:
        plaintext: String to encrypt
        
    Returns:
        str: Base64 encoded encrypted string
    """
    if not plaintext:
        return ""
    
    encrypted_bytes = cipher_suite.encrypt(plaintext.encode())
    return encrypted_bytes.decode()


def decrypt_string(ciphertext: str) -> str:
    """
    Decrypt a string encrypted with encrypt_string
    
    Args:
        ciphertext: Base64 encoded encrypted string
        
    Returns:
        str: Decrypted plaintext string
    """
    if not ciphertext:
        return ""
    
    try:
        decrypted_bytes = cipher_suite.decrypt(ciphertext.encode())
        return decrypted_bytes.decode()
    except Exception:
        # Log error in production
        return ""


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    """
    Hash a password using bcrypt
    
    Args:
        password: Password to hash
        salt: Optional salt (generated if not provided)
        
    Returns:
        tuple: (hashed_password, salt)
    """
    import bcrypt
    
    if not salt:
        salt = bcrypt.gensalt()
    
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode(), salt.decode()


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        password: Plain text password
        hashed_password: Bcrypt hashed password
        
    Returns:
        bool: True if password matches
    """
    import bcrypt
    
    try:
        return bcrypt.checkpw(password.encode(), hashed_password.encode())
    except Exception:
        return False


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token
    
    Args:
        length: Token length in bytes
        
    Returns:
        str: URL-safe base64 encoded token
    """
    import secrets
    return secrets.token_urlsafe(length)