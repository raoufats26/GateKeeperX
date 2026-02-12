from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from backend.rate_limiter import check_request
from backend.metrics import log_request, get_metrics

app = FastAPI()

@app.get("/")
def root():
    return {"message": "SentinelShield Backend Running"}

@app.get("/api/test")
async def test(request: Request):
    ip = request.client.host

    allowed = check_request(ip)

    if not allowed:
        log_request(blocked=True)
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests - Blocked by SentinelShield"}
        )

    log_request(blocked=False)
    return {"status": "Request allowed"}


@app.get("/api/metrics")
def metrics():
    return get_metrics()

