from collections import defaultdict, deque
from threading import Lock
import time


# ========================================
# GLOBAL STATE
# ========================================
total_requests = 0
allowed_requests = 0
blocked_requests = 0

ip_counter = defaultdict(int)

metrics_lock = Lock()

# Time tracking
start_time = time.time()

# Sliding window for RPS (last 10 seconds)
recent_requests = deque()

# Financial simulation
COST_PER_REQUEST = 0.000002  # $0.000002 per request


# ========================================
# REQUEST LOGGING
# ========================================
def log_request(blocked: bool, ip: str = None):
    """
    Log incoming request and update metrics.
    
    Args:
        blocked: Whether request was blocked
        ip: Client IP address
    """
    global total_requests, allowed_requests, blocked_requests

    current_time = time.time()

    with metrics_lock:
        total_requests += 1
        recent_requests.append(current_time)

        if blocked:
            blocked_requests += 1
        else:
            allowed_requests += 1

        if ip:
            ip_counter[ip] += 1


# ========================================
# METRICS RETRIEVAL
# ========================================
def get_metrics():
    """
    Get comprehensive metrics including Phase 4 financial projections.
    
    Returns:
        Dictionary with all metrics
    """
    with metrics_lock:
        current_time = time.time()
        uptime = current_time - start_time

        # =====================================
        # RPS CALCULATIONS
        # =====================================
        # Clean old timestamps (>10 sec)
        while recent_requests and current_time - recent_requests[0] > 10:
            recent_requests.popleft()

        # 10-second average RPS
        rps_last_10_sec = len(recent_requests) / 10 if recent_requests else 0

        # Instant RPS (last 1 second)
        rps_last_1_sec = len(
            [t for t in recent_requests if current_time - t <= 1]
        )

        # =====================================
        # CURRENT FINANCIAL IMPACT
        # =====================================
        # Total cost without protection
        estimated_damage_without_protection = total_requests * COST_PER_REQUEST

        # Cost saved by blocking
        estimated_cost_saved = blocked_requests * COST_PER_REQUEST

        # Actual cost with protection
        actual_cost_with_protection = allowed_requests * COST_PER_REQUEST

        # Savings percentage
        savings_percentage = (
            (estimated_cost_saved / estimated_damage_without_protection) * 100
            if estimated_damage_without_protection > 0 else 0
        )

        # =====================================
        # PHASE 4: FINANCIAL PROJECTIONS
        # =====================================
        # Hourly projections based on current RPS
        projected_hourly_requests = rps_last_10_sec * 3600
        
        projected_hourly_damage_without_protection = (
            projected_hourly_requests * COST_PER_REQUEST
        )
        
        # Apply current block rate to projection
        current_block_rate = (
            blocked_requests / total_requests if total_requests > 0 else 0
        )
        
        projected_hourly_blocked = projected_hourly_requests * current_block_rate
        projected_hourly_savings = projected_hourly_blocked * COST_PER_REQUEST
        
        # Daily projections (24 hours)
        projected_daily_requests = projected_hourly_requests * 24
        projected_daily_damage_without_protection = (
            projected_daily_requests * COST_PER_REQUEST
        )
        projected_daily_savings = projected_hourly_savings * 24

        # =====================================
        # PROTECTION EFFICIENCY
        # =====================================
        efficiency = (
            (blocked_requests / total_requests) * 100
            if total_requests > 0 else 0
        )

        # =====================================
        # TOP IPs
        # =====================================
        top_ips = sorted(
            ip_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            # ===== CORE METRICS =====
            "total_requests": total_requests,
            "allowed_requests": allowed_requests,
            "blocked_requests": blocked_requests,

            # ===== TRAFFIC ANALYTICS =====
            "rps_last_10_seconds": round(rps_last_10_sec, 2),
            "rps_last_1_second": rps_last_1_sec,
            "uptime_seconds": round(uptime, 2),

            # ===== TOP ATTACKERS =====
            "top_ips": [
                {"ip": ip, "requests": count}
                for ip, count in top_ips
            ],

            # ===== CURRENT FINANCIAL IMPACT =====
            "estimated_damage_without_protection": round(
                estimated_damage_without_protection, 6
            ),
            "actual_cost_with_protection": round(
                actual_cost_with_protection, 6
            ),
            "estimated_cost_saved": round(
                estimated_cost_saved, 6
            ),
            "savings_percentage": round(savings_percentage, 2),

            # ===== PHASE 4: ENHANCED PROJECTIONS =====
            "projected_hourly_requests": round(projected_hourly_requests, 2),
            "projected_hourly_damage": round(
                projected_hourly_damage_without_protection, 6
            ),
            "projected_hourly_savings": round(
                projected_hourly_savings, 6
            ),
            "projected_daily_requests": round(projected_daily_requests, 2),
            "projected_daily_damage": round(
                projected_daily_damage_without_protection, 6
            ),
            "projected_daily_savings": round(
                projected_daily_savings, 6
            ),

            # ===== PROTECTION EFFICIENCY =====
            "protection_efficiency_percent": round(efficiency, 2)
        }


# ========================================
# RESET METRICS
# ========================================
def reset_metrics():
    """Reset all metrics (for demo/testing)."""
    global total_requests, allowed_requests, blocked_requests, start_time

    with metrics_lock:
        total_requests = 0
        allowed_requests = 0
        blocked_requests = 0
        ip_counter.clear()
        recent_requests.clear()
        start_time = time.time()
