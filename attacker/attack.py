"""
Multi-Vector Attack Simulator for GateKeeperX WAF
Tests both legacy endpoint and new reverse proxy
"""

import requests
import threading
import time
import sys

# ========================================
# CONFIGURATION
# ========================================
BASE_URL = "http://127.0.0.1:8000"

# Attack Modes
ATTACK_MODES = {
    "1": {
        "name": "Legacy Test Endpoint",
        "url": f"{BASE_URL}/api/test",
        "description": "Original test endpoint"
    },
    "2": {
        "name": "Proxy /data Endpoint",
        "url": f"{BASE_URL}/proxy/data",
        "description": "New reverse proxy to protected backend"
    },
    "3": {
        "name": "Proxy /health Endpoint",
        "url": f"{BASE_URL}/proxy/health",
        "description": "Backend health check via proxy"
    },
    "4": {
        "name": "Proxy Root Endpoint",
        "url": f"{BASE_URL}/proxy/",
        "description": "Backend root via proxy"
    }
}

# Attack Parameters
WARMUP_REQUESTS = 30
BURST_REQUESTS = 1200
THREADS = 25

# Tracking
allowed_count = 0
blocked_count = 0
backend_errors = 0
lock = threading.Lock()


# ========================================
# ATTACK FUNCTIONS
# ========================================
def send_requests(target_url: str, total: int):
    """Send requests to target URL"""
    global allowed_count, blocked_count, backend_errors

    for _ in range(total):
        try:
            r = requests.get(target_url, timeout=5)

            with lock:
                if r.status_code == 200:
                    allowed_count += 1
                elif r.status_code == 429:
                    blocked_count += 1
                elif r.status_code >= 500:
                    backend_errors += 1
                    
        except requests.exceptions.Timeout:
            with lock:
                backend_errors += 1
        except Exception as e:
            pass  # Ignore connection errors during flood


def run_parallel(target_url: str, total_requests: int):
    """Run attack in parallel threads"""
    threads = []
    per_thread = total_requests // THREADS

    for _ in range(THREADS):
        t = threading.Thread(target=send_requests, args=(target_url, per_thread))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


# ========================================
# MAIN ATTACK FLOW
# ========================================
def main():
    global allowed_count, blocked_count, backend_errors

    print("\n" + "="*60)
    print("  GateKeeperX WAF - Attack Simulator")
    print("="*60)
    print("\nSelect attack target:\n")
    
    for key, mode in ATTACK_MODES.items():
        print(f"  [{key}] {mode['name']}")
        print(f"      → {mode['description']}")
        print(f"      → {mode['url']}\n")
    
    print("="*60)
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice not in ATTACK_MODES:
        print("❌ Invalid choice!")
        sys.exit(1)
    
    selected = ATTACK_MODES[choice]
    target_url = selected["url"]
    
    print(f"\n🎯 Target: {selected['name']}")
    print(f"🔗 URL: {target_url}")
    print(f"📊 Config: {WARMUP_REQUESTS} warmup + {BURST_REQUESTS} burst")
    print(f"🧵 Threads: {THREADS}")
    print("\n" + "="*60)
    
    # Warmup
    print("\n--- Normal Traffic Warmup ---")
    run_parallel(target_url, WARMUP_REQUESTS)
    print(f"✓ Warmup complete ({WARMUP_REQUESTS} requests)")
    
    print("\n⏱️  Attack starting in 3 seconds...\n")
    time.sleep(3)
    
    # Reset counters for burst
    allowed_count = 0
    blocked_count = 0
    backend_errors = 0
    
    print("🚨 Launching simulated HTTP flood...\n")
    start = time.time()
    
    # Attack!
    run_parallel(target_url, BURST_REQUESTS)
    
    duration = time.time() - start
    
    # Results
    print("\n" + "="*60)
    print("  ATTACK COMPLETE")
    print("="*60)
    print(f"\n📊 Statistics:")
    print(f"   Total Requests:    {WARMUP_REQUESTS + BURST_REQUESTS}")
    print(f"   Burst Requests:    {BURST_REQUESTS}")
    print(f"   ✅ Allowed:         {allowed_count}")
    print(f"   🚫 Blocked (429):   {blocked_count}")
    print(f"   ⚠️  Backend Errors:  {backend_errors}")
    print(f"\n⏱️  Duration:         {round(duration, 2)}s")
    print(f"📈 Requests/sec:     {round(BURST_REQUESTS / duration, 2)}")
    
    if blocked_count > 0:
        block_rate = (blocked_count / BURST_REQUESTS) * 100
        print(f"🛡️  Block Rate:       {round(block_rate, 2)}%")
    
    print("\n" + "="*60)
    print("💡 Check dashboard: http://127.0.0.1:8000")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Attack interrupted by user")
        sys.exit(0)