#!/bin/bash

# Start Protected Backend Server
# This simulates a customer's real application

echo "======================================"
echo "  Starting Protected Backend Server"
echo "======================================"
echo ""
echo "🏦 Service: Bank API (Mock)"
echo "🔌 Port: 9000"
echo "⚠️  This server should be accessed ONLY through SentinelShield"
echo ""

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start server
python3 protected_server/app.py
