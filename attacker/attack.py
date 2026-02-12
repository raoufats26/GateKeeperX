import requests
import threading
import time

TARGET_URL = "http://127.0.0.1:8000/api/test"

WARMUP_REQUESTS = 30
BURST_REQUESTS = 1200
THREADS = 25


allowed_count = 0
blocked_count = 0
lock = threading.Lock()


def send_requests(total):
    global allowed_count, blocked_count

    for _ in range(total):
        try:
            r = requests.get(TARGET_URL)

            with lock:
                if r.status_code == 200:
                    allowed_count += 1
                elif r.status_code == 429:
                    blocked_count += 1

        except Exception as e:
            print("Request failed:", e)


def run_parallel(total_requests):
    threads = []
    per_thread = total_requests // THREADS

    for _ in range(THREADS):
        t = threading.Thread(target=send_requests, args=(per_thread,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


def main():
    global allowed_count, blocked_count

    print("\n--- Normal Traffic Warmup ---")
    run_parallel(WARMUP_REQUESTS)

    print("Warmup complete.")
    print("\nAttack starting in 3 seconds...\n")

    time.sleep(3)

    print("Launching simulated HTTP flood...\n")

    start = time.time()

    run_parallel(BURST_REQUESTS)

    duration = time.time() - start

    print("\n===== Attack Finished =====")
    print("Total Requests:", WARMUP_REQUESTS + BURST_REQUESTS)
    print("Allowed:", allowed_count)
    print("Blocked:", blocked_count)
    print("Duration:", round(duration, 2), "seconds")
    print("Requests/sec:", round(BURST_REQUESTS / duration, 2))


if __name__ == "__main__":
    main()
