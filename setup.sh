#!/bin/bash

# ========================================
# SentinelShield v2.0 - Quick Setup
# ========================================

echo ""
echo "╔════════════════════════════════════════╗"
echo "║   SentinelShield v2.0 Quick Setup     ║"
echo "║   Reverse Proxy SaaS WAF              ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✓ Python3 found"

# Create venv if doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate venv
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Make scripts executable
chmod +x start_backend.sh start_sentinel.sh 2>/dev/null

echo ""
echo "╔════════════════════════════════════════╗"
echo "║          Setup Complete! 🎉            ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "📋 Next Steps:"
echo ""
echo "  1. Start Protected Backend (Terminal 1):"
echo "     ./start_backend.sh"
echo ""
echo "  2. Start SentinelShield WAF (Terminal 2):"
echo "     ./start_sentinel.sh"
echo ""
echo "  3. Open Dashboard:"
echo "     http://127.0.0.1:8000"
echo ""
echo "  4. Run Attack Test (Terminal 3):"
echo "     python3 attacker/attack.py"
echo ""
echo "════════════════════════════════════════"
echo ""
