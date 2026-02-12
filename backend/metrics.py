from collections import defaultdict, deque
from threading import Lock
import time


# Global Metrics State
total_requests = 0
allowed_requests = 0
blocked_requests = 0

ip_counter = defaultdict(int)
blocked_ip_counter = defaultdict(int)

metrics_lock = Lock()

# Time tracking
start_time = time.time()

# Sliding window for last 10 seconds
recent_requests = deque()

# Simulated infrastructure cost
COST_PER_REQUEST = 0.000002

# Risk scoring
total_risk_score = 0

# Attack detection threshold
ATTACK_RPS_THRESHOLD = 50
REPEAT_OFFENDER_THRESHOLD = 20

# Logging Requests
def log_request(blocked: bool, ip: str = None):
    global total_requests, allowed_requests, blocked_requests, total_risk_score

    current_time = time.time()

    with metrics_lock:
        total_requests += 1
        recent_requests.append(current_time)

        if blocked:
            blocked_requests += 1
            total_risk_score += 0.9
            if ip:
                blocked_ip_counter[ip] += 1
        else:
            allowed_requests += 1
            total_risk_score += 0.2

        if ip:
            ip_counter[ip] += 1



# Metrics Retrieval
def get_metrics():
    with metrics_lock:

        current_time = time.time()
        uptime = current_time - start_time

        # Clean old timestamps (older than 10 sec)
        while recent_requests and current_time - recent_requests[0] > 10:
            recent_requests.popleft()

        # 10-second RPS
        rps_last_10_sec = len(recent_requests) / 10

        # Instant RPS (last 1 sec)
        rps_last_1_sec = len(
            [t for t in recent_requests if current_time - t <= 1]
        )

  
        # System Mode Detection
        system_mode = (
            "UNDER_ATTACK"
            if rps_last_10_sec > ATTACK_RPS_THRESHOLD
            else "NORMAL"
        )

        # Financial Simulation
        estimated_damage_without_protection = (
            total_requests * COST_PER_REQUEST
        )

        estimated_cost_saved = (
            blocked_requests * COST_PER_REQUEST
        )

        actual_cost_with_protection = (
            allowed_requests * COST_PER_REQUEST
        )

        projected_hourly_requests = rps_last_10_sec * 3600
        projected_hourly_loss = (
            projected_hourly_requests * COST_PER_REQUEST
        )

        # Risk Analytics
        average_risk_score = (
            total_risk_score / total_requests
            if total_requests > 0 else 0
        )

        efficiency = (
            (blocked_requests / total_requests) * 100
            if total_requests > 0 else 0
        )

        savings_percentage = (
            (estimated_cost_saved / estimated_damage_without_protection) * 100
            if estimated_damage_without_protection > 0 else 0
        )

        # -----------------------------
        # Repeat Offenders
        # -----------------------------
        repeat_offender_count = len([
            ip for ip, count in blocked_ip_counter.items()
            if count >= REPEAT_OFFENDER_THRESHOLD
        ])

        # -----------------------------
        # Top 5 IPs
        # -----------------------------
        top_ips = sorted(
            ip_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            # Core
            "total_requests": total_requests,
            "allowed_requests": allowed_requests,
            "blocked_requests": blocked_requests,

            # Traffic
            "rps_last_10_seconds": round(rps_last_10_sec, 2),
            "rps_last_1_second": rps_last_1_sec,
            "uptime_seconds": round(uptime, 2),

            # System Intelligence
            "system_mode": system_mode,
            "average_risk_score": round(average_risk_score, 3),
            "repeat_offender_count": repeat_offender_count,

            # Attackers
            "top_ips": [
                {"ip": ip, "requests": count}
                for ip, count in top_ips
            ],

            # Financial
            "estimated_damage_without_protection": round(
                estimated_damage_without_protection, 6
            ),
            "actual_cost_with_protection": round(
                actual_cost_with_protection, 6
            ),
            "estimated_cost_saved": round(
                estimated_cost_saved, 6
            ),
            "projected_hourly_loss": round(
                projected_hourly_loss, 4
            ),
            "savings_percentage": round(savings_percentage, 2),

            # Protection
            "protection_efficiency_percent": round(efficiency, 2)
        }


# Reset Metrics
def reset_metrics():
    global total_requests, allowed_requests, blocked_requests
    global start_time, total_risk_score

    with metrics_lock:
        total_requests = 0
        allowed_requests = 0
        blocked_requests = 0
        total_risk_score = 0
        ip_counter.clear()
        blocked_ip_counter.clear()
        recent_requests.clear()
        start_time = time.time()
