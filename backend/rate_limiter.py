import time
from typing import Tuple, Dict

# Configuration constants
REQUEST_LIMIT = 20
WINDOW_SECONDS = 5
BLOCK_TIME = 60

# In-memory storage
ip_requests: Dict[str, list] = {}
blocked_ips: Dict[str, float] = {}


def is_allowed(ip: str) -> Tuple[bool, str]:
    """
    Check if a request from the given IP should be allowed.
    
    Returns:
        (True, "allowed") - Request is allowed
        (False, "rate_limited") - Request exceeded rate limit
        (False, "blocked") - IP is currently blocked
    """
    current_time = time.time()
    
    # Check if IP is currently blocked
    if ip in blocked_ips:
        if current_time < blocked_ips[ip]:
            return (False, "blocked")
        else:
            # Block expired, remove from blocked list
            del blocked_ips[ip]
    
    # Initialize tracking for new IP
    if ip not in ip_requests:
        ip_requests[ip] = []
    
    # Remove timestamps outside the sliding window
    ip_requests[ip] = [
        timestamp for timestamp in ip_requests[ip]
        if current_time - timestamp < WINDOW_SECONDS
    ]
    
    # Check if limit exceeded before adding current request
    if len(ip_requests[ip]) >= REQUEST_LIMIT:
        # Block the IP
        blocked_ips[ip] = current_time + BLOCK_TIME
        return (False, "rate_limited")
    
    # Add current request timestamp
    ip_requests[ip].append(current_time)
    
    return (True, "allowed")


def check_request(ip: str) -> bool:
    """
    Legacy compatibility function for existing main.py integration.
    
    Returns:
        True if request is allowed, False otherwise
    """
    allowed, _ = is_allowed(ip)
    return allowed


def get_blocked_ips() -> Dict[str, float]:
    """
    Get currently blocked IPs and their remaining block time in seconds.
    
    Returns:
        Dictionary mapping IP addresses to remaining block time in seconds
    """
    current_time = time.time()
    result = {}
    
    # Clean up expired blocks and calculate remaining time
    expired_ips = []
    for ip, block_until in blocked_ips.items():
        remaining = block_until - current_time
        if remaining > 0:
            result[ip] = remaining
        else:
            expired_ips.append(ip)
    
    # Remove expired blocks
    for ip in expired_ips:
        del blocked_ips[ip]
    
    return result