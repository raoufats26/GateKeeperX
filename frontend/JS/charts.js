let trafficChart;

function initChart() {
    const ctx = document.getElementById("trafficChart").getContext("2d");

    trafficChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Requests per Second",
                data: [],
                borderColor: "#3b82f6",
                fill: false
            }]
        },
        options: {
            animation: false,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function updateChart(value) {
    const now = new Date().toLocaleTimeString();

    trafficChart.data.labels.push(now);
    trafficChart.data.datasets[0].data.push(value);

    if (trafficChart.data.labels.length > 20) {
        trafficChart.data.labels.shift();
        trafficChart.data.datasets[0].data.shift();
    }

    trafficChart.update();
}
