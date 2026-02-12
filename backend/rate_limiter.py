import time

ip_requests = {}
blocked_ips = {}

REQUEST_LIMIT = 10
WINDOW_SECONDS = 10
BLOCK_TIME = 60

def check_request(ip: str):
    current_time = time.time()

    # Check if IP is blocked
    if ip in blocked_ips:
        if current_time < blocked_ips[ip]:
            return False
        else:
            del blocked_ips[ip]

    # Initialize if new IP
    if ip not in ip_requests:
        ip_requests[ip] = []

    # Remove old timestamps
    ip_requests[ip] = [
        timestamp for timestamp in ip_requests[ip]
        if current_time - timestamp < WINDOW_SECONDS
    ]

    # Add current request
    ip_requests[ip].append(current_time)

    # Check limit
    if len(ip_requests[ip]) > REQUEST_LIMIT:
        blocked_ips[ip] = current_time + BLOCK_TIME
        return False

    return True
