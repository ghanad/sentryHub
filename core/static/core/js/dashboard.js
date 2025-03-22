// Initialize charts when the document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize severity distribution chart
    const severityCtx = document.getElementById('severityChart').getContext('2d');
    new Chart(severityCtx, {
        type: 'doughnut',
        data: {
            labels: severityLabels,
            datasets: [{
                data: severityData,
                backgroundColor: [
                    '#dc3545',  // Critical - Red
                    '#ffc107',  // Warning - Yellow
                    '#17a2b8'   // Info - Blue
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // Initialize alert trends chart
    const trendsCtx = document.getElementById('trendsChart').getContext('2d');
    new Chart(trendsCtx, {
        type: 'line',
        data: {
            labels: trendsLabels,
            datasets: [{
                label: 'Alerts',
                data: trendsData,
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });

    // Format timestamps
    document.querySelectorAll('.timestamp').forEach(function(element) {
        const timestamp = new Date(element.getAttribute('data-timestamp'));
        element.textContent = formatTimestamp(timestamp);
    });
});

// Format timestamp to relative time
function formatTimestamp(timestamp) {
    const now = new Date();
    const diff = now - timestamp;
    
    // Convert to seconds
    const seconds = Math.floor(diff / 1000);
    
    if (seconds < 60) {
        return 'just now';
    }
    
    // Convert to minutes
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
        return `${minutes}m ago`;
    }
    
    // Convert to hours
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
        return `${hours}h ago`;
    }
    
    // Convert to days
    const days = Math.floor(hours / 24);
    if (days < 7) {
        return `${days}d ago`;
    }
    
    // If more than a week, show the date
    return timestamp.toLocaleDateString();
}

// Refresh dashboard data every 5 minutes
setInterval(function() {
    fetch('/api/dashboard2/stats/')
        .then(response => response.json())
        .then(data => {
            // Update statistics
            document.getElementById('totalAlerts').textContent = data.total_alerts;
            document.getElementById('firingAlerts').textContent = data.firing_alerts;
            document.getElementById('unacknowledgedAlerts').textContent = data.unacknowledged_alerts;
            
            // Update recent alerts table
            updateRecentAlertsTable(data.recent_alerts);
        })
        .catch(error => console.error('Error fetching dashboard data:', error));
}, 300000); // 5 minutes 