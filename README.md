🛡️ GateKeeperX v2.0 - Reverse Proxy SaaS WAF

Application-Layer Financial DoS Protection Middleware

GateKeeperX is a production-grade Web Application Firewall (WAF) that acts as a reverse proxy, protecting backend applications from Layer 7 DDoS attacks, rate limit violations, and malicious traffic.

🏗️ Architecture
┌─────────┐      ┌──────────────────┐      ┌──────────────┐
│ Client  │─────▶│ GateKeeperX WAF  │─────▶│ Protected    │
│         │      │ (Port 8000)      │      │ Backend      │
│         │◀─────│ - Rate Limiting  │◀─────│ (Port 9000)  │
└─────────┘      │ - Risk Scoring   │      └──────────────┘
                 │ - IP Blocking    │
                 │ - Defense Modes  │
                 └──────────────────┘
How It Works

Client Request → GateKeeperX intercepts all traffic

Security Check → Rate limiting, risk scoring, IP blocking

Forward → If allowed, request forwarded to protected backend

Response → Backend response returned to client

Logging → All activity logged to real-time dashboard

📁 Project Structure
gatekeeperx/
│
├── backend/
│   ├── main.py
│   ├── rate_limiter.py
│   └── metrics.py
│
├── frontend/
│   ├── index.html
│   ├── main.js
│   └── style.css
│
├── protected_server/
│   └── app.py
│
├── attacker/
│   └── attack.py
│
├── start_backend.sh
├── start_gatekeeperx.sh
│
└── venv/
🚀 Quick Start
Prerequisites
Python 3.8+
pip
Installation
python3 -m venv venv
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install fastapi uvicorn httpx requests
Optional (Linux / Mac)
chmod +x start_backend.sh start_gatekeeperx.sh
Running the System
Option 1 — Automated

Terminal 1:

./start_backend.sh

Terminal 2:

./start_gatekeeperx.sh
Option 2 — Manual

Terminal 1:

python3 protected_server/app.py

Terminal 2:

uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
Accessing the System

Dashboard

http://127.0.0.1:8000

WAF Health

http://127.0.0.1:8000/health

Proxy Endpoint

http://127.0.0.1:8000/proxy/{path}

Backend Direct

http://127.0.0.1:9000
🎯 Demo Flow
Normal Traffic Test
curl http://127.0.0.1:8000/proxy/data
curl http://127.0.0.1:8000/proxy/health

Response headers:

X-GateKeeperX: Protected
X-Protected-By: GateKeeperX-WAF-v2.0
Attack Simulation
python3 attacker/attack.py

Choose target:

[1] Legacy Test Endpoint
[2] Proxy /data Endpoint
[3] Proxy /health Endpoint
[4] Proxy Root Endpoint
Watch Dashboard

Open

http://127.0.0.1:8000

Observe:

real-time attack blocking

defense mode escalation

risk scoring

financial impact calculations

request rate charts

top attackers

🔒 Security Features
Adaptive Defense Modes
Mode	Trigger	Request Limit	Block Time
NORMAL	Default	20 req / 5s	60s
ELEVATED	30 blocked	15 req / 5s	120s
DEFENSE	100 blocked	10 req / 5s	300s
Risk Scoring Engine (0–100)

Burst Intensity
Repeat Offenses
Rate Acceleration

Exponential IP Blocking
1st Offense: 60s
2nd Offense: 90s
3rd Offense: 135s
Max: 600s
Financial Impact Tracking

Cost per request:

$0.000002

Includes:

real-time cost savings

hourly projections

daily projections

ROI metrics

📊 API Endpoints
GateKeeperX WAF
Endpoint	Method	Description
/	GET	Dashboard
/health	GET	WAF health
/proxy/{path}	ALL	Reverse proxy
/api/test	GET	Test endpoint
/api/metrics	GET	Metrics
/api/summary	GET	Summary
/api/status	GET	Status
/api/reset	POST	Reset metrics
Protected Backend
Endpoint	Method	Description
/	GET	Service info
/health	GET	Health check
/data	GET	Financial data
/accounts/{id}	GET	Account details
/transactions	POST	Create transaction
/api/metrics	GET	Backend metrics
🧪 Testing Scenarios
Normal Operation
for i in {1..10}; do
curl http://127.0.0.1:8000/proxy/data
done
Rate Limit Trigger
for i in {1..25}; do
curl http://127.0.0.1:8000/proxy/data &
done
wait
Full Attack
python3 attacker/attack.py

Choose option 2

Backend Failure

Stop backend server

Ctrl + C

Then request:

curl http://127.0.0.1:8000/proxy/data

Result:

502 Bad Gateway
🎨 Dashboard Features
Live Metrics

total requests

blocked threats

protection efficiency

requests per second

Defense Status

current defense mode

blocked IPs

threat level indicator

Financial Analytics

cost savings

projected losses avoided

Risk Intelligence

top attacking IPs

risk scores

repeat offender tracking

🔧 Configuration

Edit

backend/main.py
PROTECTED_BACKEND_URL = "http://127.0.0.1:9000"
PROXY_TIMEOUT = 30

Edit

backend/rate_limiter.py

Example:

ELEVATED_THRESHOLD = 30
DEFENSE_THRESHOLD = 100
📈 Metrics Example
{
  "total_requests": 1250,
  "allowed_requests": 50,
  "blocked_requests": 1200,
  "rps_last_10_seconds": 180.5,
  "threat_level": "HIGH",
  "defense_mode": "DEFENSE",
  "protection_efficiency_percent": 96.0,
  "estimated_cost_saved": 0.0024
}
🐛 Troubleshooting
Backend unreachable

Ensure backend is running on

port 9000
Too many blocked requests

Use

/api/reset

or reset via dashboard.

Dashboard not loading

Verify SentinelShield / GateKeeperX server is running on port 8000.

🎓 Advanced Usage
Custom Backend
PROTECTED_BACKEND_URL = "http://your-app:8080"
Multi Backend Routing
BACKEND_ROUTES = {
  "/api/v1": "http://backend-1:8000",
  "/api/v2": "http://backend-2:8000"
}
Production Deployment

Recommended:

HTTPS / TLS

authentication headers

persistent logging

Redis rate limiter

monitoring

🏆 Key Differentiators

✅ Real Reverse Proxy
✅ Adaptive Defense System
✅ Risk Intelligence Engine
✅ Financial Impact Analytics
✅ Production-grade design
✅ Real-time dashboard

📚 Learn More

FastAPI
https://fastapi.tiangolo.com

HTTPX
https://www.python-httpx.org

Rate Limiting
https://en.wikipedia.org/wiki/Rate_limiting

Layer 7 DDoS
https://www.cloudflare.com/learning/ddos/what-is-layer-7/

🎉 Success Criteria

✔ Backend runs on port 9000
✔ GateKeeperX runs on port 8000
✔ Proxy forwards requests correctly
✔ Rate limiting blocks attacks
✔ Defense modes escalate automatically
✔ Dashboard updates live
✔ Financial metrics calculate correctly

Built with ❤️ for Hackathon

GateKeeperX — Turn your backend into a fortress. 🛡️
