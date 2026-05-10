(function () {
    function palette() {
        return ["#1266d6", "#0f9f9a", "#1f9d55", "#f59e0b", "#dc3545", "#6d5dfc"];
    }

    function makeDoughnut(id, labels, values) {
        const element = document.getElementById(id);
        if (!element || !window.Chart) {
            return;
        }
        new Chart(element, {
            type: "doughnut",
            data: {
                labels,
                datasets: [{ data: values, backgroundColor: palette(), borderWidth: 0 }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: "bottom" }
                }
            }
        });
    }

    function makeBar(id, labels, values) {
        const element = document.getElementById(id);
        if (!element || !window.Chart) {
            return;
        }
        new Chart(element, {
            type: "bar",
            data: {
                labels,
                datasets: [{ data: values, backgroundColor: "#0f9f9a", borderRadius: 8 }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });
    }

    if (window.HealthPilotCharts) {
        makeDoughnut("statusChart", window.HealthPilotCharts.statusLabels, window.HealthPilotCharts.statusValues);
        makeBar("serviceChart", window.HealthPilotCharts.serviceLabels, window.HealthPilotCharts.serviceValues);
    }

    if (window.HealthPilotAdminCharts) {
        makeDoughnut("adminAppointmentChart", window.HealthPilotAdminCharts.appointmentLabels, window.HealthPilotAdminCharts.appointmentValues);
        makeBar("adminHospitalChart", window.HealthPilotAdminCharts.hospitalLabels, window.HealthPilotAdminCharts.hospitalValues);
    }
})();
