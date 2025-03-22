document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Function to format duration
    function formatDuration(seconds) {
        if (seconds < 60) {
            return seconds + " seconds";
        } else if (seconds < 3600) {
            return Math.floor(seconds / 60) + " min " + (seconds % 60) + " sec";
        } else if (seconds < 86400) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return hours + " hr " + minutes + " min";
        } else {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            return days + " days " + hours + " hr";
        }
    }

    // Calculate durations for completed periods
    document.querySelectorAll('.duration').forEach(function(el) {
        const start = new Date(el.dataset.start);
        const end = new Date(el.dataset.end);
        const duration = Math.floor((end - start) / 1000); // Duration in seconds
        el.textContent = formatDuration(duration);
    });
    
    // Calculate ongoing durations
    document.querySelectorAll('.ongoing-duration').forEach(function(el) {
        const start = new Date(el.dataset.start);
        const now = new Date();
        const duration = Math.floor((now - start) / 1000); // Duration in seconds
        el.textContent = formatDuration(duration) + " (ongoing)";
        
        // Update ongoing duration every minute
        setInterval(function() {
            const currentDuration = Math.floor((new Date() - start) / 1000);
            el.textContent = formatDuration(currentDuration) + " (ongoing)";
        }, 60000);
    });
    
    // Create history chart
    function createHistoryChart() {
        try {
            // Populate from instances data
            const instanceData = JSON.parse(document.getElementById('historyChart').dataset.instances);
            
            const historyData = {
                labels: [],
                datasets: [{
                    label: 'Alert Status',
                    data: [],
                    backgroundColor: [],
                    borderColor: [],
                    borderWidth: 1,
                    barThickness: 20
                }]
            };
            
            instanceData.forEach(instance => {
                historyData.labels.push(instance.label);
                const isFiring = instance.status === "firing" && !instance.ended_at;
                historyData.datasets[0].data.push(isFiring ? 1 : 0);
                historyData.datasets[0].backgroundColor.push(
                    isFiring ? 'rgba(220, 53, 69, 0.6)' : 'rgba(25, 135, 84, 0.6)'
                );
                historyData.datasets[0].borderColor.push(
                    isFiring ? 'rgb(220, 53, 69)' : 'rgb(25, 135, 84)'
                );
            });
            
            if (historyData.labels.length > 0) {
                const ctx = document.getElementById('historyChart').getContext('2d');
                new Chart(ctx, {
                    type: 'bar',
                    data: historyData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 1,
                                ticks: {
                                    callback: function(value) {
                                        return value === 0 ? 'Resolved' : 'Firing';
                                    }
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return context.raw === 1 ? 'Status: Firing' : 'Status: Resolved';
                                    }
                                }
                            }
                        }
                    }
                });
            }
        } catch (e) {
            console.error("Error creating chart:", e);
            document.getElementById('historyChart').innerHTML = '<div class="alert alert-warning">Could not load chart data</div>';
        }
    }

    // Initialize chart
    if (document.getElementById('historyChart')) {
        createHistoryChart();
    }
}); 