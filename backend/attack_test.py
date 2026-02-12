import requests

URL = "http://127.0.0.1:8000/api/test"

for i in range(50):
    r = requests.get(URL)
    print(i, r.status_code)
