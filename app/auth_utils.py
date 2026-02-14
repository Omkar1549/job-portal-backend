import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import re

# Relative imports
try:
    from . import database, models
except ImportError:
    import database
    import models

# Configure logging
logger = logging.getLogger(__name__)

# --- SECURITY CONFIGURATION ---

# Get secrets from environment variables (never hardcode!)
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "your-super-secret-key-change-in-production"  # CHANGE THIS!
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Validate SECRET_KEY length (minimum 32 characters)
if len(SECRET_KEY) < 32:
    logger.warning(
        "SECRET_KEY is too short (< 32 chars). "
        "Using a weak key compromises security!"
    )

# Password hashing configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Cost factor for bcrypt (higher = slower but more secure)
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login",
    scopes={
        "read": "Read access",
        "write": "Write access",
        "admin": "Admin access"
    }
)


# --- PASSWORD HASHING ---

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against hashed password
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# --- PASSWORD VALIDATION ---

PASSWORD_REQUIREMENTS = {
    "min_length": 8,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digit": True,
    "require_special": True,
}

SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    errors = []
    
    # Minimum length
    if len(password) < PASSWORD_REQUIREMENTS["min_length"]:
        errors.append(f"Password must be at least {PASSWORD_REQUIREMENTS['min_length']} characters")
    
    # Uppercase requirement
    if PASSWORD_REQUIREMENTS["require_uppercase"] and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Lowercase requirement
    if PASSWORD_REQUIREMENTS["require_lowercase"] and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Digit requirement
    if PASSWORD_REQUIREMENTS["require_digit"] and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    
    # Special character requirement
    if PASSWORD_REQUIREMENTS["require_special"] and not any(c in SPECIAL_CHARS for c in password):
        errors.append(f"Password must contain at least one special character: {SPECIAL_CHARS}")
    
    if errors:
        return False, " | ".join(errors)
    
    return True, ""


def validate_email_format(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# --- JWT TOKEN MANAGEMENT ---

class TokenPayload:
    """Token payload data structure"""
    def __init__(self, email: str, user_id: int, role: str, exp: datetime):
        self.email = email
        self.user_id = user_id
        self.role = role
        self.exp = exp


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    
    Args:
        data: Data to encode (should contain 'sub' for email)
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at
        "type": "access"  # Token type
    })
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Access token created for: {data.get('sub')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token
    
    Args:
        data: Data to encode (should contain 'sub' for email)
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"  # Token type
    })
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Refresh token created for: {data.get('sub')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise


def verify_token(token: str) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token to verify
        
    Returns:
        Tuple of (is_valid, payload)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True, payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return False, None


# --- AUTHENTICATION DEPENDENCIES ---

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db)
) -> models.User:
    """
    Get current authenticated user from token
    
    Args:
        token: JWT token from Authorization header
        db: Database session
        
    Returns:
        Current user model
        
    Raises:
        HTTPException: If token invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify and decode token
        is_valid, payload = verify_token(token)
        
        if not is_valid or payload is None:
            logger.warning("Invalid token provided")
            raise credentials_exception
        
        # Extract email from token
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
        
        # Prevent using refresh token as access token
        if token_type == "refresh":
            logger.warning("Attempted to use refresh token as access token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise credentials_exception
    
    # Get user from database
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if user is None:
        logger.warning(f"User not found: {email}")
        raise credentials_exception
    
    if not user.is_active:
        logger.warning(f"Inactive user tried to login: {email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    # Update last login
    try:
        user.last_login = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger.error(f"Error updating last_login: {e}")
        db.rollback()
    
    return user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Verify user is active
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User if active
        
    Raises:
        HTTPException: If user inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# --- ROLE-BASED ACCESS CONTROL ---

def admin_required(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """
    Require admin role
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User if admin
        
    Raises:
        HTTPException: If not admin
    """
    if current_user.role != "admin":
        logger.warning(f"Unauthorized access attempt by: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def recruiter_required(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """
    Require recruiter or admin role
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User if recruiter or admin
        
    Raises:
        HTTPException: If not recruiter/admin
    """
    if current_user.role not in ["recruiter", "admin"]:
        logger.warning(f"Unauthorized recruiter access attempt by: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter privileges required"
        )
    return current_user


def candidate_required(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """
    Require candidate or admin role
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User if candidate or admin
        
    Raises:
        HTTPException: If not candidate/admin
    """
    if current_user.role not in ["candidate", "admin"]:
        logger.warning(f"Unauthorized candidate access attempt by: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate access required"
        )
    return current_user


def owner_or_admin(
    resource_owner_id: int,
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """
    Check if user is resource owner or admin
    
    Args:
        resource_owner_id: ID of resource owner
        current_user: Current authenticated user
        
    Returns:
        User if owner or admin
        
    Raises:
        HTTPException: If neither owner nor admin
    """
    if current_user.id != resource_owner_id and current_user.role != "admin":
        logger.warning(
            f"Unauthorized resource access by {current_user.email} "
            f"(owner_id: {resource_owner_id})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )
    return current_user


# --- RATE LIMITING HELPER ---

from functools import wraps
from time import time

# Simple in-memory rate limiter
_rate_limit_store = {}


def rate_limit(max_requests: int, time_window: int):
    """
    Rate limit decorator (max_requests per time_window seconds)
    
    Args:
        max_requests: Maximum requests allowed
        time_window: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get user email from current_user if available
            user_email = None
            for arg in args:
                if isinstance(arg, models.User):
                    user_email = arg.email
                    break
            
            if not user_email:
                return func(*args, **kwargs)
            
            current_time = time()
            key = f"{user_email}:{func.__name__}"
            
            if key not in _rate_limit_store:
                _rate_limit_store[key] = []
            
            # Remove old requests outside time window
            _rate_limit_store[key] = [
                req_time for req_time in _rate_limit_store[key]
                if current_time - req_time < time_window
            ]
            
            # Check if limit exceeded
            if len(_rate_limit_store[key]) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {max_requests} requests per {time_window}s"
                )
            
            _rate_limit_store[key].append(current_time)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# --- SESSION MANAGEMENT ---

class SessionManager:
    """Manage user sessions"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, user_id: int, token: str) -> str:
        """Create user session"""
        session_id = f"{user_id}:{datetime.utcnow().timestamp()}"
        self._sessions[session_id] = {
            "user_id": user_id,
            "token": token,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
        return session_id
    
    def is_session_valid(self, session_id: str, max_inactive_hours: int = 24) -> bool:
        """Check if session is valid"""
        if session_id not in self._sessions:
            return False
        
        session = self._sessions[session_id]
        last_activity = session["last_activity"]
        time_since_activity = (datetime.utcnow() - last_activity).total_seconds() / 3600
        
        return time_since_activity < max_inactive_hours
    
    def update_activity(self, session_id: str):
        """Update session last activity time"""
        if session_id in self._sessions:
            self._sessions[session_id]["last_activity"] = datetime.utcnow()
    
    def invalidate_session(self, session_id: str):
        """Invalidate (logout) session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def invalidate_user_sessions(self, user_id: int):
        """Logout all sessions for a user"""
        keys_to_delete = [
            key for key, session in self._sessions.items()
            if session["user_id"] == user_id
        ]
        for key in keys_to_delete:
            del self._sessions[key]


session_manager = SessionManager()