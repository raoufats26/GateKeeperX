import time
import hashlib
import redis
from typing import Dict
from threading import Lock

# ========================================
# REDIS CONNECTION
# ========================================
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

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
MAX_BLOCK_TIME = 600

ELEVATED_THRESHOLD = 30
DEFENSE_THRESHOLD = 100

current_defense_mode = "NORMAL"
mode_lock = Lock()

# ========================================
# STORAGE (Still local for analytics)
# ========================================
blocked_ips: Dict[str, float] = {}
offense_count: Dict[str, int] = {}
risk_scores: Dict[str, float] = {}
last_request_time: Dict[str, float] = {}
storage_lock = Lock()

# ========================================
# HELPER FUNCTIONS
# ========================================
def fingerprint(ip: str) -> str:
    """Create stable client fingerprint."""
    return hashlib.sha256(ip.encode()).hexdigest()


# ========================================
# RISK SCORING ENGINE
# ========================================
def calculate_risk_score(ip: str, current_time: float, request_count: int) -> float:
    risk = 0.0

    burst_score = min(40, (request_count / 20) * 40)
    risk += burst_score

    if ip in offense_count:
        offenses = offense_count[ip]
        risk += min(40, offenses * 10)

    if ip in last_request_time:
        delta = current_time - last_request_time[ip]
        if delta < 0.1:
            risk += 20
        elif delta < 0.5:
            risk += 10

    risk = min(100.0, risk)

    risk_scores[ip] = risk
    last_request_time[ip] = current_time

    return risk


# ========================================
# DEFENSE MODE STATE MACHINE
# ========================================
def get_defense_mode(total_blocked: int) -> str:
    if total_blocked >= DEFENSE_THRESHOLD:
        return "DEFENSE"
    elif total_blocked >= ELEVATED_THRESHOLD:
        return "ELEVATED"
    return "NORMAL"


def update_defense_mode(total_blocked: int):
    global current_defense_mode
    new_mode = get_defense_mode(total_blocked)

    with mode_lock:
        if new_mode != current_defense_mode:
            current_defense_mode = new_mode
            print(f"🛡️ DEFENSE MODE CHANGED: {current_defense_mode}")


def get_current_mode_config() -> dict:
    with mode_lock:
        return MODE_CONFIGS[current_defense_mode].copy()


# ========================================
# ADAPTIVE RATE LIMITER (REDIS VERSION)
# ========================================
def check_request(ip: str, total_blocked: int = 0) -> bool:
    current_time = time.time()

    update_defense_mode(total_blocked)

    config = get_current_mode_config()
    request_limit = config["request_limit"]
    window_seconds = config["window_seconds"]
    base_block_time = config["base_block_time"]

    fp = fingerprint(ip)
    window_id = int(current_time / window_seconds)
    redis_key = f"rate:{fp}:{window_id}"

    # Atomic increment
    current_count = redis_client.incr(redis_key)
    redis_client.expire(redis_key, window_seconds)

    with storage_lock:
        if ip in blocked_ips:
            if current_time < blocked_ips[ip]:
                return False
            else:
                del blocked_ips[ip]

        risk = calculate_risk_score(ip, current_time, current_count)

        if current_count > request_limit:
            offense_count[ip] = offense_count.get(ip, 0) + 1

            block_duration = base_block_time * (
                SEVERITY_MULTIPLIER ** offense_count[ip]
            )
            block_duration = min(block_duration, MAX_BLOCK_TIME)

            blocked_ips[ip] = current_time + block_duration

            print(
                f"🚫 BLOCKED {ip} | Offense #{offense_count[ip]} "
                f"| Risk {risk:.1f} | Block {block_duration:.0f}s"
            )

            return False

        return True


# ========================================
# MONITORING
# ========================================
def get_blocked_ips() -> Dict[str, float]:
    current_time = time.time()
    result = {}
    expired = []

    with storage_lock:
        for ip, until in blocked_ips.items():
            remaining = until - current_time
            if remaining > 0:
                result[ip] = round(remaining, 2)
            else:
                expired.append(ip)

        for ip in expired:
            del blocked_ips[ip]

    return result


def get_risk_analytics() -> dict:
    with storage_lock:
        top_risk = sorted(
            risk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        top_offenders = sorted(
            offense_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        avg_risk = (
            sum(risk_scores.values()) / len(risk_scores)
            if risk_scores else 0
        )

        return {
            "defense_mode": current_defense_mode,
            "mode_config": get_current_mode_config(),
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
    with mode_lock:
        return current_defense_mode


# ========================================
# RESET
# ========================================
def reset_rate_limiter():
    global current_defense_mode

    with storage_lock:
        blocked_ips.clear()
        offense_count.clear()
        risk_scores.clear()
        last_request_time.clear()

    redis_client.flushdb()

    with mode_lock:
        current_defense_mode = "NORMAL"

    print("🔄 Rate limiter reset - NORMAL MODE")
