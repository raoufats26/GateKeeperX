from collections import defaultdict
from threading import Lock

# -----------------------------
# Global Metrics State
# -----------------------------
total_requests = 0
allowed_requests = 0
blocked_requests = 0

ip_counter = defaultdict(int)

metrics_lock = Lock()

# Simulated serverless cost per request
COST_PER_REQUEST = 0.000002


# -----------------------------
# Logging Requests
# -----------------------------
def log_request(blocked: bool, ip: str = None):
    global total_requests, allowed_requests, blocked_requests

    with metrics_lock:
        total_requests += 1

        if blocked:
            blocked_requests += 1
        else:
            allowed_requests += 1

        if ip:
            ip_counter[ip] += 1


# -----------------------------
# Metrics Retrieval
# -----------------------------
def get_metrics():
    with metrics_lock:
        estimated_cost_saved = blocked_requests * COST_PER_REQUEST

        top_ips = sorted(
            ip_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "total_requests": total_requests,
            "allowed_requests": allowed_requests,
            "blocked_requests": blocked_requests,
            "top_ips": [
                {"ip": ip, "requests": count}
                for ip, count in top_ips
            ],
            "estimated_cost_saved": round(estimated_cost_saved, 8)
        }


# -----------------------------
# Reset Metrics (For Demo)
# -----------------------------
def reset_metrics():
    global total_requests, allowed_requests, blocked_requests

    with metrics_lock:
        total_requests = 0
        allowed_requests = 0
        blocked_requests = 0
        ip_counter.clear()