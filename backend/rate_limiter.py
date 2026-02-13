import time
import hashlib
import redis
from typing import Dict, Tuple, Optional
from threading import Lock
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rate_limiter")

# ========================================
# REDIS CONNECTION WITH ERROR HANDLING
# ========================================
try:
    redis_client = redis.Redis(
        host="127.0.0.1",  # Changed from localhost to 127.0.0.1 for Windows compatibility
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test connection immediately
    redis_client.ping()
    logger.info("✅ Redis connection successful!")
    REDIS_AVAILABLE = True
except redis.ConnectionError as e:
    logger.error(f"❌ Redis connection failed: {e}")
    logger.warning("⚠️  Falling back to in-memory storage")
    redis_client = None
    REDIS_AVAILABLE = False

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

# Defense mode thresholds (optimized for demo)
ELEVATED_THRESHOLD = 30   # Triggers faster for demo
DEFENSE_THRESHOLD = 100   # Triggers faster for demo

# Current defense mode
current_defense_mode = "NORMAL"
mode_lock = Lock()


# ========================================
# STORAGE (Fallback for when Redis unavailable)
# ========================================
# Local storage for analytics AND fallback
blocked_ips: Dict[str, float] = {}
offense_count: Dict[str, int] = {}
risk_scores: Dict[str, float] = {}
last_request_time: Dict[str, float] = {}
ip_requests: Dict[str, list] = {}  # Fallback for rate limiting
storage_lock = Lock()


# ========================================
# HELPER FUNCTIONS
# ========================================
def fingerprint(ip: str) -> str:
    """
    Create stable client fingerprint using SHA256.
    Provides privacy and consistency across distributed instances.
    """
    return hashlib.sha256(ip.encode()).hexdigest()[:16]  # Shortened for readability


def get_redis_stats() -> dict:
    """Get Redis statistics for debugging."""
    if not REDIS_AVAILABLE or redis_client is None:
        return {
            "available": False,
            "total_keys": 0,
            "keys": []
        }
    
    try:
        all_keys = redis_client.keys("*")
        return {
            "available": True,
            "total_keys": len(all_keys),
            "keys": all_keys[:20]  # First 20 keys
        }
    except Exception as e:
        logger.error(f"Error getting Redis stats: {e}")
        return {
            "available": False,
            "error": str(e)
        }


# ========================================
# ADVANCED RISK SCORING ENGINE
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
    
    # Factor 1: Burst Intensity (0-40 points)
    burst_score = min(40, (request_count / 20) * 40)
    risk += burst_score
    
    # Factor 2: Repeat Offenses (0-40 points)
    # Check both Redis and local storage
    offenses = 0
    if REDIS_AVAILABLE and redis_client:
        try:
            redis_offenses = redis_client.get(f"offense:{ip}")
            if redis_offenses:
                offenses = int(redis_offenses)
        except Exception as e:
            logger.debug(f"Redis offense lookup failed: {e}")
    
    if ip in offense_count:
        offenses = max(offenses, offense_count[ip])
    
    if offenses > 0:
        offense_score = min(40, offenses * 10)
        risk += offense_score
    
    # Factor 3: Rate Acceleration (0-20 points)
    if ip in last_request_time:
        time_diff = current_time - last_request_time[ip]
        if time_diff < 0.1:  # Very rapid (< 100ms)
            risk += 20
        elif time_diff < 0.5:  # Rapid (< 500ms)
            risk += 10
    
    # Clamp to 0-100 range
    risk = min(100.0, risk)
    
    # Update tracking (both Redis and local)
    risk_scores[ip] = risk
    last_request_time[ip] = current_time
    
    if REDIS_AVAILABLE and redis_client:
        try:
            redis_client.setex(f"risk:{ip}", 3600, str(risk))  # 1 hour TTL
        except Exception as e:
            logger.debug(f"Redis risk update failed: {e}")
    
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
            logger.info(f"🛡️  DEFENSE MODE CHANGED: {current_defense_mode} (blocked: {total_blocked})")
            
            # Store in Redis
            if REDIS_AVAILABLE and redis_client:
                try:
                    redis_client.set("defense_mode", current_defense_mode)
                except Exception as e:
                    logger.debug(f"Redis defense mode update failed: {e}")


def get_current_mode_config() -> dict:
    """Get current mode configuration - thread-safe."""
    with mode_lock:
        return MODE_CONFIGS[current_defense_mode].copy()


# ========================================
# ADAPTIVE RATE LIMITER (REDIS + FALLBACK)
# ========================================
def check_request(ip: str, total_blocked: int = 0) -> bool:
    """
    Main entry point - Adaptive intelligent rate limiter with Redis backend.
    
    Features:
    - Redis-based distributed rate limiting (when available)
    - Automatic fallback to in-memory storage
    - Advanced 3-factor risk scoring
    - Dynamic defense modes
    - Offender memory with exponential blocking
    - Client fingerprinting for privacy
    
    Args:
        ip: Client IP address
        total_blocked: Current total blocked requests (for defense mode)
    
    Returns:
        bool: True if request allowed, False if blocked
    """
    current_time = time.time()
    
    # Update defense mode based on attack intensity
    update_defense_mode(total_blocked)
    
    # Get current mode configuration
    config = get_current_mode_config()
    request_limit = config["request_limit"]
    window_seconds = config["window_seconds"]
    base_block_time = config["base_block_time"]
    
    # Create fingerprint for Redis key
    fp = fingerprint(ip)
    
    # === REDIS-BASED RATE LIMITING ===
    if REDIS_AVAILABLE and redis_client:
        try:
            # Use time-based window ID for sliding window
            window_id = int(current_time / window_seconds)
            redis_key = f"rate:{fp}:{window_id}"
            
            # ATOMIC INCREMENT
            current_count = redis_client.incr(redis_key)
            redis_client.expire(redis_key, int(window_seconds * 2))  # 2x window for safety
            
            logger.debug(f"[REDIS] Key: {redis_key} | Count: {current_count}/{request_limit}")
            
        except Exception as e:
            logger.error(f"❌ Redis error, falling back to local storage: {e}")
            # Fall through to local storage
            current_count = _check_request_local(ip, current_time, window_seconds)
    else:
        # Use local storage
        current_count = _check_request_local(ip, current_time, window_seconds)
    
    # === CRITICAL SECTION FOR BLOCKING LOGIC ===
    with storage_lock:
        # Check if IP is currently blocked (check both Redis and local)
        is_blocked = False
        block_until = 0
        
        if REDIS_AVAILABLE and redis_client:
            try:
                redis_block = redis_client.get(f"block:{ip}")
                if redis_block:
                    block_until = float(redis_block)
                    if current_time < block_until:
                        is_blocked = True
            except Exception as e:
                logger.debug(f"Redis block check failed: {e}")
        
        # Also check local storage
        if ip in blocked_ips:
            local_block_until = blocked_ips[ip]
            if current_time < local_block_until:
                is_blocked = True
                block_until = max(block_until, local_block_until)
        
        if is_blocked:
            remaining = block_until - current_time
            logger.debug(f"🚫 IP {ip} still blocked ({remaining:.1f}s remaining)")
            return False  # Still blocked
        
        # Cleanup expired blocks
        if ip in blocked_ips and current_time >= blocked_ips[ip]:
            del blocked_ips[ip]
            if REDIS_AVAILABLE and redis_client:
                try:
                    redis_client.delete(f"block:{ip}")
                except Exception:
                    pass
        
        # Calculate advanced risk score (3-factor algorithm)
        risk = calculate_risk_score(ip, current_time, current_count)
        
        # Check if limit exceeded
        if current_count > request_limit:
            # Record offense for repeat tracking
            if ip not in offense_count:
                offense_count[ip] = 0
            offense_count[ip] += 1
            
            # Store offense in Redis
            if REDIS_AVAILABLE and redis_client:
                try:
                    redis_client.incr(f"offense:{ip}")
                    redis_client.expire(f"offense:{ip}", 86400)  # 24 hour TTL
                    logger.debug(f"[REDIS] Incremented offense count for {ip}")
                except Exception as e:
                    logger.debug(f"Redis offense update failed: {e}")
            
            # Calculate exponential block duration
            block_duration = base_block_time * (SEVERITY_MULTIPLIER ** offense_count[ip])
            block_duration = min(block_duration, MAX_BLOCK_TIME)
            
            # Block the IP (both Redis and local)
            blocked_ips[ip] = current_time + block_duration
            
            if REDIS_AVAILABLE and redis_client:
                try:
                    redis_client.setex(
                        f"block:{ip}",
                        int(block_duration + 10),  # Add buffer
                        str(current_time + block_duration)
                    )
                    logger.info(f"[REDIS] ✅ Blocked {ip} in Redis for {block_duration:.0f}s")
                except Exception as e:
                    logger.error(f"Redis block storage failed: {e}")
            
            logger.warning(
                f"🚫 BLOCKED {ip} | Offense #{offense_count[ip]} "
                f"| Risk: {risk:.1f} | Block: {block_duration:.0f}s | Count: {current_count}/{request_limit}"
            )
            
            return False  # BLOCKED
        
        # Request allowed
        logger.debug(f"✅ ALLOWED {ip} | Risk: {risk:.1f} | Count: {current_count}/{request_limit}")
        return True  # ALLOWED


def _check_request_local(ip: str, current_time: float, window_seconds: float) -> int:
    """Fallback local rate limiting using in-memory storage."""
    with storage_lock:
        if ip not in ip_requests:
            ip_requests[ip] = []
        
        # Sliding window cleanup
        ip_requests[ip] = [
            ts for ts in ip_requests[ip]
            if current_time - ts < window_seconds
        ]
        
        # Add current request
        ip_requests[ip].append(current_time)
        
        return len(ip_requests[ip])


# ========================================
# MONITORING & ANALYTICS
# ========================================
def get_blocked_ips() -> Dict[str, float]:
    """Get blocked IPs and remaining time - thread-safe."""
    current_time = time.time()
    result = {}
    expired = []
    
    with storage_lock:
        # Check local storage
        for ip, block_until in blocked_ips.items():
            remaining = block_until - current_time
            if remaining > 0:
                result[ip] = round(remaining, 2)
            else:
                expired.append(ip)
        
        # Also check Redis
        if REDIS_AVAILABLE and redis_client:
            try:
                block_keys = redis_client.keys("block:*")
                for key in block_keys:
                    ip = key.replace("block:", "")
                    block_until_str = redis_client.get(key)
                    if block_until_str:
                        block_until = float(block_until_str)
                        remaining = block_until - current_time
                        if remaining > 0:
                            result[ip] = round(remaining, 2)
            except Exception as e:
                logger.debug(f"Redis blocked IPs fetch failed: {e}")
        
        # Cleanup expired blocks
        for ip in expired:
            del blocked_ips[ip]
    
    return result


def get_risk_analytics() -> dict:
    """Get comprehensive risk analytics - thread-safe."""
    with storage_lock:
        # Top 5 highest risk IPs
        top_risk = sorted(
            risk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Top 5 repeat offenders
        top_offenders = sorted(
            offense_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Average risk score across all tracked IPs
        avg_risk = 0.0
        if risk_scores:
            avg_risk = sum(risk_scores.values()) / len(risk_scores)
        
        current_mode = get_current_mode_config()
        
        return {
            "defense_mode": current_defense_mode,
            "mode_config": current_mode,
            "redis_available": REDIS_AVAILABLE,
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
    """Reset all state - clears both Redis and local storage."""
    global current_defense_mode
    
    # Clear local analytics
    with storage_lock:
        blocked_ips.clear()
        offense_count.clear()
        risk_scores.clear()
        last_request_time.clear()
        ip_requests.clear()
    
    # Flush Redis database
    if REDIS_AVAILABLE and redis_client:
        try:
            redis_client.flushdb()
            logger.info("[REDIS] ✅ Flushed all keys")
        except Exception as e:
            logger.error(f"Redis flush failed: {e}")
    
    # Reset defense mode
    with mode_lock:
        current_defense_mode = "NORMAL"
    
    logger.info("🔄 Rate limiter reset - NORMAL MODE")