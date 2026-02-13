"""
Protected Backend Server - Mock Customer Application
This simulates a customer's real backend that SentinelShield protects.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time
import random

app = FastAPI(
    title="Protected Bank API",
    description="Mock customer backend protected by SentinelShield",
    version="1.0.0"
)

# Simulated database
ACCOUNTS = {
    "ACC001": {"balance": 150000.50, "name": "Enterprise Account"},
    "ACC002": {"balance": 42000.00, "name": "Premium Account"},
    "ACC003": {"balance": 8500.25, "name": "Standard Account"}
}

# Request counter
request_count = 0
start_time = time.time()


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "bank-api",
        "status": "operational",
        "message": "Protected by SentinelShield WAF",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    """Health check endpoint"""
    global request_count
    request_count += 1
    
    uptime = round(time.time() - start_time, 2)
    
    return {
        "status": "healthy",
        "service": "bank-api",
        "uptime_seconds": uptime,
        "requests_served": request_count,
        "timestamp": time.time()
    }


@app.get("/data")
def get_data():
    """Main data endpoint - simulates sensitive financial data"""
    global request_count
    request_count += 1
    
    # Simulate some processing time
    time.sleep(random.uniform(0.01, 0.05))
    
    return {
        "service": "bank-api",
        "status": "operational",
        "data": {
            "accounts_count": len(ACCOUNTS),
            "total_balance": sum(acc["balance"] for acc in ACCOUNTS.values()),
            "timestamp": time.time(),
            "message": "Financial data served successfully"
        },
        "metadata": {
            "request_id": f"REQ-{request_count}",
            "processing_time_ms": round(random.uniform(10, 50), 2)
        }
    }


@app.get("/accounts/{account_id}")
def get_account(account_id: str):
    """Get specific account - simulates sensitive endpoint"""
    global request_count
    request_count += 1
    
    if account_id not in ACCOUNTS:
        return JSONResponse(
            status_code=404,
            content={"error": "Account not found", "account_id": account_id}
        )
    
    # Simulate processing
    time.sleep(random.uniform(0.01, 0.03))
    
    account = ACCOUNTS[account_id]
    
    return {
        "account_id": account_id,
        "name": account["name"],
        "balance": account["balance"],
        "currency": "USD",
        "timestamp": time.time()
    }


@app.post("/transactions")
async def create_transaction(request: Request):
    """Simulate transaction creation"""
    global request_count
    request_count += 1
    
    try:
        body = await request.json()
    except:
        body = {}
    
    # Simulate processing
    time.sleep(random.uniform(0.02, 0.08))
    
    return {
        "status": "success",
        "transaction_id": f"TXN-{random.randint(100000, 999999)}",
        "amount": body.get("amount", 0),
        "timestamp": time.time(),
        "message": "Transaction processed successfully"
    }


@app.get("/api/metrics")
def backend_metrics():
    """Backend's own metrics"""
    global request_count
    
    uptime = round(time.time() - start_time, 2)
    
    return {
        "service": "bank-api",
        "uptime_seconds": uptime,
        "total_requests": request_count,
        "requests_per_second": round(request_count / max(uptime, 1), 2),
        "status": "healthy"
    }


if __name__ == "__main__":
    import uvicorn
    print("🏦 Protected Bank API starting on port 9000...")
    print("⚠️  This server should be protected by SentinelShield")
    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="info")
