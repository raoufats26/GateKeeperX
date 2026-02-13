#!/bin/bash

# Start SentinelShield WAF (Reverse Proxy)

echo "======================================"
echo "  Starting SentinelShield WAF v2.0"
echo "======================================"
echo ""
echo "🛡️  Mode: Reverse Proxy WAF"
echo "🔌 Port: 8000"
echo "🔗 Protected Backend: http://127.0.0.1:9000"
echo "📊 Dashboard: http://127.0.0.1:8000"
echo ""
echo "⚠️  Make sure protected backend is running on port 9000!"
echo ""

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start SentinelShield
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
