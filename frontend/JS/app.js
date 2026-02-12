initChart();

async function updateDashboard() {
    try {
        const data = await fetchMetrics();

        // Update stat cards
        document.getElementById("totalRequests").innerText =
            data.total_requests;

        document.getElementById("blockedRequests").innerText =
            data.blocked_requests;

        document.getElementById("allowedRequests").innerText =
            data.allowed_requests;

        document.getElementById("costSaved").innerText =
            "$" + data.estimated_cost_saved.toFixed(6);

        // Update top IP table
        updateTopIps(data.top_ips);

        // Update chart
        updateChart(data.requests_per_second);

    } catch (error) {
        console.error("Error fetching metrics:", error);
    }
}

function updateTopIps(topIps) {
    const tbody = document.querySelector("#topIpsTable tbody");
    tbody.innerHTML = "";  // Clear old rows

    topIps.forEach(ip => {
        const row = `
            <tr>
                <td>${ip.address}</td>
                <td>${ip.count}</td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}


// Poll every second
setInterval(updateDashboard, 1000);
