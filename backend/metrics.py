total_requests = 0
blocked_requests = 0

# Simulated serverless cost per request
COST_PER_REQUEST = 0.000002


def log_request(blocked: bool):
    global total_requests, blocked_requests

    total_requests += 1

    if blocked:
        blocked_requests += 1


def calculate_cost_saved():
    return blocked_requests * COST_PER_REQUEST


def get_metrics():
    return {
        "total_requests": total_requests,
        "blocked_requests": blocked_requests,
        "allowed_requests": total_requests - blocked_requests,
        "estimated_cost_saved": round(calculate_cost_saved(), 6)
    }
