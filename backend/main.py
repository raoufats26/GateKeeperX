from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import httpx
from typing import Optional

from backend.rate_limiter import (
    check_request, 
    get_blocked_ips, 
    get_risk_analytics,
    get_defense_mode_status,
    reset_rate_limiter
)
from backend.metrics import log_request, get_metrics, reset_metrics

# ========================================
# CONFIGURATION
# ========================================
PROTECTED_BACKEND_URL = "http://127.0.0.1:9000"
PROXY_TIMEOUT = 30.0  # seconds

app = FastAPI(
    title="SentinelShield WAF",
    description="Reverse Proxy SaaS WAF - Application-Layer Financial DoS Protection",
    version="2.0.0"
)

# ========================================
# CORS
# ========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# LOGGING
# ========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sentinelshield")

# ========================================
# HTTP CLIENT FOR PROXYING
# ========================================
http_client: Optional[httpx.AsyncClient] = None


@app.on_event("startup")
async def startup_event():
    """Initialize HTTP client on startup"""
    global http_client
    http_client = httpx.AsyncClient(
        timeout=PROXY_TIMEOUT,
        follow_redirects=False
    )
    logger.info("🛡️  SentinelShield WAF initialized")
    logger.info(f"🔗 Protected backend: {PROTECTED_BACKEND_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup HTTP client on shutdown"""
    global http_client
    if http_client:
        await http_client.aclose()
    logger.info("🛡️  SentinelShield WAF shutdown")


# ========================================
# GLOBAL EXCEPTION HANDLER
# ========================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "SentinelShield internal protection error"}
    )


# ========================================
# ROOT → DASHBOARD
# ========================================
@app.get("/")
def root():
    """Serve dashboard"""
    return FileResponse("frontend/index.html")


# ========================================
# HEALTH CHECK
# ========================================
@app.get("/health")
def health_check():
    """SentinelShield health check"""
    return {
        "status": "healthy",
        "service": "SentinelShield WAF",
        "version": "2.0.0",
        "mode": "reverse_proxy"
    }


# ========================================
# REVERSE PROXY ENDPOINT (NEW!)
# ========================================
@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def reverse_proxy(request: Request, path: str):
    """
    Reverse Proxy Endpoint - Core WAF Functionality
    
    This endpoint:
    1. Intercepts all client requests
    2. Applies rate limiting & risk scoring
    3. Forwards allowed requests to protected backend
    4. Returns backend response to client
    5. Logs all activity to dashboard
    """
    # Extract client IP
    ip = request.client.host
    
    logger.info(f"[PROXY] {request.method} /{path} from {ip}")
    
    # Get current metrics for adaptive defense mode
    current_metrics = get_metrics()
    
    # === RATE LIMITING & PROTECTION ===
    allowed = check_request(ip, current_metrics["blocked_requests"])
    
    if not allowed:
        logger.warning(f"[BLOCKED] {ip} → /{path}")
        log_request(blocked=True, ip=ip)
        
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too Many Requests - Blocked by SentinelShield WAF",
                "service": "SentinelShield",
                "blocked": True
            },
            headers={
                "X-SentinelShield": "Blocked",
                "X-Rate-Limit-Exceeded": "true"
            }
        )
    
    # === FORWARD TO PROTECTED BACKEND ===
    try:
        # Build target URL
        target_url = f"{PROTECTED_BACKEND_URL}/{path}"
        
        # Add query parameters
        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"
        
        # Prepare headers (filter sensitive ones)
        headers = dict(request.headers)
        headers_to_remove = ["host", "content-length"]
        for header in headers_to_remove:
            headers.pop(header, None)
        
        # Add SentinelShield headers
        headers["X-Forwarded-For"] = ip
        headers["X-SentinelShield-Protected"] = "true"
        headers["X-Original-IP"] = ip
        
        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Forward request to backend
        logger.info(f"[FORWARD] {request.method} {target_url}")
        
        response = await http_client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body
        )
        
        # Log successful proxy
        logger.info(f"[RESPONSE] {response.status_code} from backend for {ip}")
        log_request(blocked=False, ip=ip)
        
        # Return backend response to client
        return JSONResponse(
            status_code=response.status_code,
            content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"data": response.text},
            headers={
                "X-SentinelShield": "Protected",
                "X-Protected-By": "SentinelShield-WAF-v2.0"
            }
        )
        
    except httpx.ConnectError:
        logger.error(f"[ERROR] Cannot connect to protected backend: {PROTECTED_BACKEND_URL}")
        log_request(blocked=False, ip=ip)  # Count as allowed but failed
        
        return JSONResponse(
            status_code=502,
            content={
                "detail": "Protected backend unavailable",
                "service": "SentinelShield",
                "error": "backend_unreachable"
            }
        )
        
    except httpx.TimeoutException:
        logger.error(f"[ERROR] Backend timeout for /{path}")
        log_request(blocked=False, ip=ip)
        
        return JSONResponse(
            status_code=504,
            content={
                "detail": "Protected backend timeout",
                "service": "SentinelShield",
                "error": "backend_timeout"
            }
        )
        
    except Exception as e:
        logger.error(f"[ERROR] Proxy error: {e}")
        log_request(blocked=False, ip=ip)
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Proxy error",
                "service": "SentinelShield",
                "error": str(e)
            }
        )


# ========================================
# ORIGINAL TEST ENDPOINT (PRESERVED)
# ========================================
@app.get("/api/test")
async def test(request: Request):
    """
    Original test endpoint - preserved for backward compatibility
    """
    ip = request.client.host
    logger.info(f"Incoming request from {ip}")

    # Pass blocked count for adaptive mode
    current_metrics = get_metrics()
    allowed = check_request(ip, current_metrics["blocked_requests"])

    if not allowed:
        logger.warning(f"Blocked IP: {ip}")
        log_request(blocked=True, ip=ip)
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests - Blocked by SentinelShield"}
        )

    log_request(blocked=False, ip=ip)
    response = JSONResponse(content={"status": "Request allowed"})
    response.headers["X-SentinelShield"] = "Protected"
    return response


# ========================================
# METRICS (ENHANCED)
# ========================================
@app.get("/api/metrics")
def metrics():
    """Enhanced metrics including proxy statistics"""
    data = get_metrics()
    
    # Add active blocked IPs
    data["active_blocked_ips"] = get_blocked_ips()

    # Calculate threat level
    blocked = data["blocked_requests"]
    total = data["total_requests"]

    if blocked == 0:
        threat_level = "LOW"
    elif blocked < 50:
        threat_level = "MEDIUM"
    else:
        threat_level = "HIGH"

    efficiency = 0
    if total > 0:
        efficiency = round((blocked / total) * 100, 2)

    data["attack_detected"] = blocked > 0
    data["threat_level"] = threat_level
    data["protection_efficiency_percent"] = efficiency

    # Add risk analytics
    risk_analytics = get_risk_analytics()
    
    data["defense_mode"] = risk_analytics["defense_mode"]
    data["mode_config"] = risk_analytics["mode_config"]
    data["risk_analytics"] = {
        "top_risk_ips": risk_analytics["top_risk_ips"],
        "top_offenders": risk_analytics["top_offenders"],
        "average_risk_score": risk_analytics["average_risk_score"],
        "total_tracked_ips": risk_analytics["total_tracked_ips"],
        "total_repeat_offenders": risk_analytics["total_repeat_offenders"]
    }
    
    # Add WAF-specific metadata
    data["waf_mode"] = "reverse_proxy"
    data["protected_backend"] = PROTECTED_BACKEND_URL

    return data


# ========================================
# SUMMARY
# ========================================
@app.get("/api/summary")
def protection_summary():
    """Protection summary"""
    data = get_metrics()
    total = data["total_requests"]
    blocked = data["blocked_requests"]

    efficiency = 0
    if total > 0:
        efficiency = round((blocked / total) * 100, 2)

    return {
        "system_name": "SentinelShield WAF",
        "version": "2.0",
        "mode": "reverse_proxy",
        "requests_processed": total,
        "threats_blocked": blocked,
        "protection_efficiency_percent": efficiency,
        "estimated_cost_saved": data["estimated_cost_saved"],
        "defense_mode": get_defense_mode_status(),
        "protected_backend": PROTECTED_BACKEND_URL
    }


# ========================================
# STATUS
# ========================================
@app.get("/api/status")
def api_status():
    """API status"""
    blocked_ips = get_blocked_ips()
    defense_mode = get_defense_mode_status()
    
    return {
        "status": "protected",
        "active_blocked_ips": len(blocked_ips),
        "shield": "SentinelShield WAF v2.0",
        "defense_mode": defense_mode,
        "mode": "reverse_proxy",
        "backend": PROTECTED_BACKEND_URL
    }


# ========================================
# RESET
# ========================================
@app.post("/api/reset")
def reset():
    """Reset all metrics and rate limiter"""
    reset_metrics()
    reset_rate_limiter()
    logger.info("System reset performed")
    
    return {
        "status": "System reset successfully",
        "metrics": "cleared",
        "rate_limiter": "cleared",
        "defense_mode": "NORMAL"
    }


# ========================================
# STATIC FILES (MUST BE LAST)
# ========================================
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
