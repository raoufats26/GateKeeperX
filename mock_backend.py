from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from random import randint, choice
from fastapi.responses import JSONResponse
import time

app = FastAPI()

# Allow frontend running on a different port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fake in-memory metrics
metrics = {
    "total_requests": 0,
    "blocked_requests": 0,
    "allowed_requests": 0,
    "estimated_cost_saved": 0.0,
    "requests_per_second": 0,
    "top_ips": []
}

IP_POOL = ["192.168.1.10", "10.0.0.5", "172.16.0.3", "192.168.0.7", "10.0.0.8"]
COST_PER_REQUEST = 0.000002
LAST_UPDATE = time.time()

@app.get("/api/metrics")
def get_metrics():
    global LAST_UPDATE
    # simulate new requests every second
    now = time.time()
    delta = now - LAST_UPDATE
    if delta >= 1.0:
        new_requests = randint(50, 200)  # random traffic spike
        blocked = randint(0, new_requests // 2)
        allowed = new_requests - blocked

        metrics["total_requests"] += new_requests
        metrics["blocked_requests"] += blocked
        metrics["allowed_requests"] += allowed
        metrics["estimated_cost_saved"] = metrics["blocked_requests"] * COST_PER_REQUEST
        metrics["requests_per_second"] = new_requests

        # Randomly update top IPs
        metrics["top_ips"] = [
            {"address": ip, "count": randint(10, 100)}
            for ip in IP_POOL
        ]
        LAST_UPDATE = now

    return JSONResponse(metrics)
