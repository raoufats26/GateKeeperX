import time
from typing import Dict, Tuple
from threading import Lock

# ========================================
# CONFIGURATION - DEFENSE MODES
# ========================================
MODE_CONFIGS = {
    "NORMAL": {
        "request_limit": 20,
        "window_seconds": 5,
        "base_block_time": 60
    },
    "ELEVATED": {
        "request_limit": 15,
        "window_seconds": 5,
        "base_block_time": 120
    },
    "DEFENSE": {
        "request_limit": 10,
        "window_seconds": 5,
        "base_block_time": 300
    }
}

SEVERITY_MULTIPLIER = 1.5
MAX_BLOCK_TIME = 600  # 10 minutes max

# Defense mode thresholds (LOWERED for faster demo)
ELEVATED_THRESHOLD = 30   # Was 100 - now triggers faster
DEFENSE_THRESHOLD = 100   # Was 300 - now triggers faster

# Current defense mode
current_defense_mode = "NORMAL"
mode_lock = Lock()


# ========================================
# STORAGE
# ========================================
ip_requests: Dict[str, list] = {}
blocked_ips: Dict[str, float] = {}
offense_count: Dict[str, int] = {}
risk_scores: Dict[str, float] = {}
last_request_time: Dict[str, float] = {}
storage_lock = Lock()


# ========================================
# RISK SCORING ENGINE
# ========================================
def calculate_risk_score(ip: str, current_time: float, request_count: int) -> float:
    """
    Calculate dynamic risk score (0-100) based on:
    - Request burst intensity (0-40 pts)
    - Repeat offense history (0-40 pts)
    - Rate acceleration (0-20 pts)
    
    Must be called within storage_lock.
    """
    risk = 0.0
    
    # Factor 1: Burst Intensity
    burst_score = min(40, (request_count / 20) * 40)
    risk += burst_score
    
    # Factor 2: Repeat Offenses
    if ip in offense_count:
        offenses = offense_count[ip]
        offense_score = min(40, offenses * 10)
        risk += offense_score
    
    # Factor 3: Rate Acceleration
    if ip in last_request_time:
        time_diff = current_time - last_request_time[ip]
        if time_diff < 0.1:  # Very rapid
            risk += 20
        elif time_diff < 0.5:
            risk += 10
    
    risk = min(100.0, risk)
    risk_scores[ip] = risk
    last_request_time[ip] = current_time
    
    return risk


# ========================================
# DEFENSE MODE STATE MACHINE
# ========================================
def get_defense_mode(total_blocked: int) -> str:
    """
    Determine defense mode based on blocked count.
    NORMAL → ELEVATED → DEFENSE
    """
    if total_blocked >= DEFENSE_THRESHOLD:
        return "DEFENSE"
    elif total_blocked >= ELEVATED_THRESHOLD:
        return "ELEVATED"
    else:
        return "NORMAL"


def update_defense_mode(total_blocked: int):
    """Update global defense mode based on attack intensity."""
    global current_defense_mode
    
    new_mode = get_defense_mode(total_blocked)
    
    with mode_lock:
        if new_mode != current_defense_mode:
            current_defense_mode = new_mode
            print(f"🛡️  DEFENSE MODE CHANGED: {current_defense_mode} (blocked: {total_blocked})")


def get_current_mode_config() -> dict:
    """Get current mode configuration - thread-safe."""
    with mode_lock:
        return MODE_CONFIGS[current_defense_mode].copy()


# ========================================
# ADAPTIVE RATE LIMITER
# ========================================
def check_request(ip: str, total_blocked: int = 0) -> bool:
    """
    Main entry point - Adaptive intelligent rate limiter.
    All logic in ONE lock for thread safety.
    
    Features:
    - Dynamic defense modes
    - Risk scoring
    - Offender memory
    - Exponential blocking
    """
    current_time = time.time()
    
    # Update defense mode
    update_defense_mode(total_blocked)
    
    # Get current mode config
    config = get_current_mode_config()
    request_limit = config["request_limit"]
    window_seconds = config["window_seconds"]
    base_block_time = config["base_block_time"]
    
    # === CRITICAL SECTION ===
    with storage_lock:
        # Check if blocked
        if ip in blocked_ips:
            if current_time < blocked_ips[ip]:
                return False  # Still blocked
            else:
                # Block expired
                if ip in blocked_ips:
                    del blocked_ips[ip]
                if ip in ip_requests:
                    del ip_requests[ip]
        
        # Initialize tracking
        if ip not in ip_requests:
            ip_requests[ip] = []
        
        # Sliding window cleanup
        ip_requests[ip] = [
            ts for ts in ip_requests[ip]
            if current_time - ts < window_seconds
        ]
        
        # Get current count
        current_count = len(ip_requests[ip])
        
        # Calculate risk score
        risk = calculate_risk_score(ip, current_time, current_count)
        
        # Check limit
        if current_count >= request_limit:
            # Record offense
            if ip not in offense_count:
                offense_count[ip] = 0
            offense_count[ip] += 1
            
            # Calculate block duration
            block_duration = base_block_time * (SEVERITY_MULTIPLIER ** offense_count[ip])
            block_duration = min(block_duration, MAX_BLOCK_TIME)
            
            # Block IP
            blocked_ips[ip] = current_time + block_duration
            
            print(f"🚫 BLOCKED {ip} | Offense #{offense_count[ip]} | Risk: {risk:.1f} | Block: {block_duration:.0f}s")
            
            return False  # BLOCKED
        
        # Allow request
        ip_requests[ip].append(current_time)
        return True  # ALLOWED


# ========================================
# MONITORING & ANALYTICS
# ========================================
def get_blocked_ips() -> Dict[str, float]:
    """Get blocked IPs and remaining time - thread-safe."""
    current_time = time.time()
    result = {}
    expired = []
    
    with storage_lock:
        for ip, block_until in blocked_ips.items():
            remaining = block_until - current_time
            if remaining > 0:
                result[ip] = round(remaining, 2)
            else:
                expired.append(ip)
        
        # Cleanup expired
        for ip in expired:
            if ip in blocked_ips:
                del blocked_ips[ip]
            if ip in ip_requests:
                del ip_requests[ip]
    
    return result


def get_risk_analytics() -> dict:
    """Get comprehensive risk analytics - thread-safe."""
    with storage_lock:
        # Top 5 risk IPs
        top_risk = sorted(
            risk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Top 5 offenders
        top_offenders = sorted(
            offense_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Average risk
        avg_risk = 0.0
        if risk_scores:
            avg_risk = sum(risk_scores.values()) / len(risk_scores)
        
        current_mode = get_current_mode_config()
        
        return {
            "defense_mode": current_defense_mode,
            "mode_config": current_mode,
            "top_risk_ips": [
                {"ip": ip, "risk_score": round(score, 2)}
                for ip, score in top_risk
            ],
            "top_offenders": [
                {"ip": ip, "offense_count": count}
                for ip, count in top_offenders
            ],
            "average_risk_score": round(avg_risk, 2),
            "total_tracked_ips": len(risk_scores),
            "total_repeat_offenders": len(offense_count)
        }


def get_defense_mode_status() -> str:
    """Get current defense mode - thread-safe."""
    with mode_lock:
        return current_defense_mode


# ========================================
# RESET
# ========================================
def reset_rate_limiter():
    """Reset all state."""
    global current_defense_mode
    
    with storage_lock:
        ip_requests.clear()
        blocked_ips.clear()
        offense_count.clear()
        risk_scores.clear()
        last_request_time.clear()
    
    with mode_lock:
        current_defense_mode = "NORMAL"
    
    print("🔄 Rate limiter reset - NORMAL MODE")
