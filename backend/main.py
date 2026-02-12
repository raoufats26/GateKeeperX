from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from backend.rate_limiter import (
    check_request, 
    get_blocked_ips, 
    get_risk_analytics,
    get_defense_mode_status,
    reset_rate_limiter
)
from backend.metrics import log_request, get_metrics, reset_metrics

app = FastAPI(
    title="SentinelShield API",
    description="Application-Layer Financial DoS Protection Middleware",
    version="2.0.0"
)

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinelshield")


# -----------------------------
# Global Exception Handler
# -----------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "SentinelShield internal protection error"}
    )


# -----------------------------
# Root → Dashboard
# -----------------------------
@app.get("/")
def root():
    return FileResponse("frontend/index.html")


# -----------------------------
# Health Check
# -----------------------------
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}


# -----------------------------
# Protected Test Endpoint
# -----------------------------
@app.get("/api/test")
async def test(request: Request):
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


# -----------------------------
# Metrics (Phase 4 Enhanced)
# -----------------------------
@app.get("/api/metrics")
def metrics():
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

    # Core backward-compatible fields
    data["attack_detected"] = blocked > 0
    data["threat_level"] = threat_level
    data["protection_efficiency_percent"] = efficiency

    # ===== PHASE 4: NEW INTELLIGENCE FIELDS =====
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

    return data


# -----------------------------
# Summary
# -----------------------------
@app.get("/api/summary")
def protection_summary():
    data = get_metrics()
    total = data["total_requests"]
    blocked = data["blocked_requests"]

    efficiency = 0
    if total > 0:
        efficiency = round((blocked / total) * 100, 2)

    return {
        "system_name": "SentinelShield",
        "version": "2.0",
        "requests_processed": total,
        "threats_blocked": blocked,
        "protection_efficiency_percent": efficiency,
        "estimated_cost_saved": data["estimated_cost_saved"],
        "defense_mode": get_defense_mode_status()
    }


# -----------------------------
# Status
# -----------------------------
@app.get("/api/status")
def api_status():
    blocked_ips = get_blocked_ips()
    defense_mode = get_defense_mode_status()
    
    return {
        "status": "protected",
        "active_blocked_ips": len(blocked_ips),
        "shield": "SentinelShield v2.0",
        "defense_mode": defense_mode
    }


# -----------------------------
# Reset (Enhanced)
# -----------------------------
@app.post("/api/reset")
def reset():
    reset_metrics()
    reset_rate_limiter()
    return {
        "status": "System reset successfully",
        "metrics": "cleared",
        "rate_limiter": "cleared",
        "defense_mode": "NORMAL"
    }


# -----------------------------
# Static files – MUST be LAST
# -----------------------------
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
