import time
from typing import Tuple, Dict

# Configuration constants
REQUEST_LIMIT = 20
WINDOW_SECONDS = 10
BLOCK_TIME = 60

# In-memory storage
ip_requests: Dict[str, list] = {}
blocked_ips: Dict[str, float] = {}


def is_allowed(ip: str) -> Tuple[bool, str]:
    current_time = time.time()

    # Check if IP is currently blocked
    if ip in blocked_ips:
        if current_time < blocked_ips[ip]:
            return (False, "blocked")
        else:
            del blocked_ips[ip]

    # Initialize tracking for new IP
    if ip not in ip_requests:
        ip_requests[ip] = []

    # Remove timestamps outside sliding window
    ip_requests[ip] = [
        timestamp for timestamp in ip_requests[ip]
        if current_time - timestamp < WINDOW_SECONDS
    ]

    # Check rate limit
    if len(ip_requests[ip]) >= REQUEST_LIMIT:
        blocked_ips[ip] = current_time + BLOCK_TIME
        return (False, "rate_limited")

    # Add request timestamp
    ip_requests[ip].append(current_time)

    return (True, "allowed")


def check_request(ip: str) -> bool:
    allowed, _ = is_allowed(ip)
    return allowed


def get_blocked_ips() -> Dict[str, float]:
    current_time = time.time()
    result = {}

    expired_ips = []

    for ip, block_until in blocked_ips.items():
        remaining = block_until - current_time
        if remaining > 0:
            result[ip] = round(remaining, 2)
        else:
            expired_ips.append(ip)

    for ip in expired_ips:
        del blocked_ips[ip]

    return result
