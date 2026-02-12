from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from backend.rate_limiter import check_request, get_blocked_ips
from backend.metrics import log_request, get_metrics, reset_metrics

app = FastAPI(
    title="SentinelShield API",
    description="Application-Layer Financial DoS Protection Middleware",
    version="1.0.0"
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
    return {"status": "healthy"}


# -----------------------------
# Protected Test Endpoint
# -----------------------------
@app.get("/api/test")
async def test(request: Request):
    ip = request.client.host
    logger.info(f"Incoming request from {ip}")

    allowed = check_request(ip)

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
# Metrics
# -----------------------------
@app.get("/api/metrics")
def metrics():
    data = get_metrics()
    data["active_blocked_ips"] = get_blocked_ips()

    blocked = data["blocked_requests"]
    total   = data["total_requests"]

    if blocked == 0:
        threat_level = "LOW"
    elif blocked < 50:
        threat_level = "MEDIUM"
    else:
        threat_level = "HIGH"

    efficiency = 0
    if total > 0:
        efficiency = round((blocked / total) * 100, 2)

    data["attack_detected"]               = blocked > 0
    data["threat_level"]                  = threat_level
    data["protection_efficiency_percent"] = efficiency

    return data


# -----------------------------
# Summary
# -----------------------------
@app.get("/api/summary")
def protection_summary():
    data    = get_metrics()
    total   = data["total_requests"]
    blocked = data["blocked_requests"]

    efficiency = 0
    if total > 0:
        efficiency = round((blocked / total) * 100, 2)

    return {
        "system_name": "SentinelShield",
        "version": "1.0",
        "requests_processed": total,
        "threats_blocked": blocked,
        "protection_efficiency_percent": efficiency,
        "estimated_cost_saved": data["estimated_cost_saved"]
    }


# -----------------------------
# Status
# -----------------------------
@app.get("/api/status")
def api_status():
    blocked_ips = get_blocked_ips()
    return {
        "status": "protected",
        "active_blocked_ips": len(blocked_ips),
        "shield": "SentinelShield v1.0"
    }


# -----------------------------
# Reset
# -----------------------------
@app.post("/api/reset")
def reset():
    reset_metrics()
    return {"status": "Metrics reset successfully"}


# -----------------------------
# Static files — MUST be LAST
# -----------------------------
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
