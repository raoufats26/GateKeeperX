import time
import hashlib
from typing import Dict, Optional

# ========================================
# CONFIGURATION
# ========================================
REQUEST_LIMIT = 20
WINDOW_SECONDS = 5
BASE_BLOCK_TIME = 60
SEVERITY_MULTIPLIER = 2


# ========================================
# STORAGE
# ========================================
# Track request timestamps per fingerprint
fingerprint_requests: Dict[str, list] = {}

# Track blocked fingerprints and their unblock time
blocked_fingerprints: Dict[str, float] = {}

# Track severity level per fingerprint (number of violations)
severity: Dict[str, int] = {}


# ========================================
# FINGERPRINTING
# ========================================
def generate_fingerprint(ip: str, user_agent: Optional[str] = None) -> str:
    """
    Generate a unique fingerprint for client identification.
    
    Args:
        ip: Client IP address (mandatory)
        user_agent: Client User-Agent string (optional)
        
    Returns:
        Unique fingerprint string
    """
    if user_agent is None:
        # Use IP only for backward compatibility
        return ip
    
    # Combine IP and User-Agent for enhanced fingerprinting
    fingerprint_data = f"{ip}:{user_agent}"
    fingerprint_hash = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    return f"{ip}_{fingerprint_hash}"


# ========================================
# CORE LIMITER
# ========================================
def _intelligent_rate_limiter(fingerprint: str) -> bool:
    """
    Intelligent adaptive rate limiter with dynamic blocking and fingerprinting.
    
    Features:
    - Sliding window rate limiting
    - Exponential block duration escalation
    - Automatic cooldown reset
    
    Args:
        fingerprint: Client fingerprint identifier
        
    Returns:
        True if request is allowed, False if blocked or rate limited
    """
    current_time = time.time()
    
    # Check if fingerprint is currently blocked
    if fingerprint in blocked_fingerprints:
        if current_time < blocked_fingerprints[fingerprint]:
            # Still blocked - deny request
            return False
        else:
            # Block expired - perform cooldown reset
            _cooldown_reset(fingerprint)
    
    # Initialize tracking for new fingerprint
    if fingerprint not in fingerprint_requests:
        fingerprint_requests[fingerprint] = []
    
    # Sliding window cleanup: remove timestamps outside the window
    fingerprint_requests[fingerprint] = [
        timestamp for timestamp in fingerprint_requests[fingerprint]
        if current_time - timestamp < WINDOW_SECONDS
    ]
    
    # Check if rate limit exceeded
    if len(fingerprint_requests[fingerprint]) >= REQUEST_LIMIT:
        # Increase severity counter for this fingerprint
        if fingerprint not in severity:
            severity[fingerprint] = 0
        severity[fingerprint] += 1
        
        # Calculate dynamic adaptive block duration using exponential scaling
        block_duration = BASE_BLOCK_TIME * (SEVERITY_MULTIPLIER ** severity[fingerprint])
        
        # Block the fingerprint with adaptive duration
        blocked_fingerprints[fingerprint] = current_time + block_duration
        
        return False
    
    # Add current request timestamp
    fingerprint_requests[fingerprint].append(current_time)
    
    return True


# ========================================
# COOLDOWN RESET
# ========================================
def _cooldown_reset(fingerprint: str):
    """
    Reset all tracking data for a fingerprint after block expires.
    
    Prevents memory leaks and cleanly resets protection state.
    
    Args:
        fingerprint: Client fingerprint to reset
    """
    # Remove from blocked fingerprints
    if fingerprint in blocked_fingerprints:
        del blocked_fingerprints[fingerprint]
    
    # Remove request history
    if fingerprint in fingerprint_requests:
        del fingerprint_requests[fingerprint]
    
    # Reset severity counter
    if fingerprint in severity:
        del severity[fingerprint]


# ========================================
# COMPATIBILITY WRAPPER
# ========================================
def check_request(ip: str) -> bool:
    """
    Compatibility function for FastAPI middleware integration.
    MUST NOT be modified - required by main.py.
    
    This function maintains backward compatibility while internally
    using the intelligent fingerprint-based rate limiter.
    
    Args:
        ip: IP address to check
        
    Returns:
        True if request is allowed, False otherwise
    """
    # Generate fingerprint from IP (user_agent=None for compatibility)
    fingerprint = generate_fingerprint(ip, user_agent=None)
    
    # Call intelligent rate limiter
    return _intelligent_rate_limiter(fingerprint)


# ========================================
# MONITORING
# ========================================
def get_blocked_ips() -> Dict[str, float]:
    """
    Get currently blocked fingerprints and their remaining block time.
    
    Returns:
        Dictionary mapping fingerprints to remaining block time in seconds
    """
    current_time = time.time()
    result = {}
    expired_fingerprints = []
    
    # Calculate remaining time and identify expired blocks
    for fingerprint, block_until in blocked_fingerprints.items():
        remaining = block_until - current_time
        if remaining > 0:
            result[fingerprint] = round(remaining, 2)
        else:
            expired_fingerprints.append(fingerprint)
    
    # Perform cooldown reset for expired blocks
    for fingerprint in expired_fingerprints:
        _cooldown_reset(fingerprint)
    
    return result