import requests
import time
import threading

TARGET_URL = "http://127.0.0.1:8000/api/test"
TOTAL_REQUESTS = 1000
THREADS = 20  # number of parallel attackers


allowed_count = 0
blocked_count = 0
lock = threading.Lock()


def send_requests(num_requests: int):
    global allowed_count, blocked_count

    for _ in range(num_requests):
        try:
            response = requests.get(TARGET_URL)

            with lock:
                if response.status_code == 200:
                    allowed_count += 1
                elif response.status_code == 429:
                    blocked_count += 1

            print("Status:", response.status_code)

        except Exception as e:
            print("Request failed:", e)


def main():
    print("Starting attack simulation...\n")

    start_time = time.time()

    requests_per_thread = TOTAL_REQUESTS // THREADS
    threads = []

    for _ in range(THREADS):
        t = threading.Thread(
            target=send_requests,
            args=(requests_per_thread,)
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    duration = time.time() - start_time

    print("\n===== Attack Finished =====")
    print("Total Requests Sent:", TOTAL_REQUESTS)
    print("Allowed:", allowed_count)
    print("Blocked:", blocked_count)
    print("Duration:", round(duration, 2), "seconds")
    print("Requests/sec:", round(TOTAL_REQUESTS / duration, 2))


if __name__ == "__main__":
    main()
