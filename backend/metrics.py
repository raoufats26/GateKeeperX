total_requests = 0
blocked_requests = 0

def log_request(blocked: bool):
    global total_requests, blocked_requests

    total_requests += 1

    if blocked:
        blocked_requests += 1

def get_metrics():
    return {
        "total_requests": total_requests,
        "blocked_requests": blocked_requests,
        "allowed_requests": total_requests - blocked_requests
    }
