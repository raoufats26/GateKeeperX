const BASE_URL = "http://localhost:5500";

async function fetchMetrics() {
    const response = await fetch(`${BASE_URL}/api/metrics`);
    const data = await response.json();
    return data;
}
