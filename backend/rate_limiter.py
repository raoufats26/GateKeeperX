import time
from typing import Dict

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
# Track request timestamps per IP
ip_requests: Dict[str, list] = {}

# Track blocked IPs and their unblock time
blocked_ips: Dict[str, float] = {}

# Track severity level per IP (number of violations)
severity: Dict[str, int] = {}


# ========================================
# CORE LOGIC
# ========================================
def _adaptive_rate_limiter(ip: str) -> bool:
    """
    Adaptive intelligent rate limiter with escalating block duration.
    
    Returns:
        True if request is allowed, False if blocked or rate limited
    """
    current_time = time.time()
    
    # Check if IP is currently blocked
    if ip in blocked_ips:
        if current_time < blocked_ips[ip]:
            # Still blocked
            return False
        else:
            # Block expired - perform cooldown reset
            _cooldown_reset(ip)
    
    # Initialize tracking for new IP
    if ip not in ip_requests:
        ip_requests[ip] = []
    
    # Sliding window: remove timestamps outside the window
    ip_requests[ip] = [
        timestamp for timestamp in ip_requests[ip]
        if current_time - timestamp < WINDOW_SECONDS
    ]
    
    # Check if rate limit exceeded
    if len(ip_requests[ip]) >= REQUEST_LIMIT:
        # Increase severity counter for this IP
        if ip not in severity:
            severity[ip] = 0
        severity[ip] += 1
        
        # Calculate adaptive block duration
        block_duration = BASE_BLOCK_TIME * (SEVERITY_MULTIPLIER ** (severity[ip] - 1))
        
        # Block the IP with adaptive duration
        blocked_ips[ip] = current_time + block_duration
        
        return False
    
    # Add current request timestamp
    ip_requests[ip].append(current_time)
    
    return True


def _cooldown_reset(ip: str):
    """
    Reset all tracking data for an IP after block expires.
    Prevents memory growth and resets attack state.
    """
    # Remove from blocked IPs
    if ip in blocked_ips:
        del blocked_ips[ip]
    
    # Remove request history
    if ip in ip_requests:
        del ip_requests[ip]
    
    # Reset severity counter
    if ip in severity:
        del severity[ip]


# ========================================
# COMPATIBILITY WRAPPER
# ========================================
def check_request(ip: str) -> bool:
    """
    Compatibility function for FastAPI middleware integration.
    MUST NOT be modified - required by main.py.
    
    Args:
        ip: IP address to check
        
    Returns:
        True if request is allowed, False otherwise
    """
    return _adaptive_rate_limiter(ip)


# ========================================
# MONITORING
# ========================================
def get_blocked_ips() -> Dict[str, float]:
    """
    Get currently blocked IPs and their remaining block time.
    
    Returns:
        Dictionary mapping IP addresses to remaining block time in seconds
    """
    current_time = time.time()
    result = {}
    expired_ips = []
    
    # Calculate remaining time and identify expired blocks
    for ip, block_until in blocked_ips.items():
        remaining = block_until - current_time
        if remaining > 0:
            result[ip] = round(remaining, 2)
        else:
            expired_ips.append(ip)
    
    # Perform cooldown reset for expired blocks
    for ip in expired_ips:
        _cooldown_reset(ip)
    
    return result