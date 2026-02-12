from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.rate_limiter import check_request, get_blocked_ips
from backend.metrics import log_request, get_metrics

app = FastAPI(title="SentinelShield API")

# -----------------------------
# CORS (Safe for frontend)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Logging Setup
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
# Root Endpoint
# -----------------------------
@app.get("/")
def root():
    return {"message": "SentinelShield Backend Running"}


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
        log_request(blocked=True)
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests - Blocked by SentinelShield"}
        )

    log_request(blocked=False)
    return {"status": "Request allowed"}


# -----------------------------
# Metrics Endpoint
# -----------------------------
@app.get("/api/metrics")
def metrics():
    data = get_metrics()
    data["active_blocked_ips"] = get_blocked_ips()
    data["attack_detected"] = data["blocked_requests"] > 0
    return data
