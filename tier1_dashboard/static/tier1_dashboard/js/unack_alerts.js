// JavaScript for unacknowledged alerts page

// Auto-refresh functionality
(function() {
    const refreshInterval = 30000; // 30 seconds
    let refreshTimer;
    const refreshBadge = document.getElementById('refresh-badge');
    let countdown = refreshInterval / 1000;

    function updateBadge() {
        if (refreshBadge) {
            refreshBadge.textContent = `Auto-Refresh: ${countdown}s`;
            countdown--;
            if (countdown < 0) countdown = refreshInterval / 1000;
        }
    }

    function scheduleRefresh() {
        clearTimeout(refreshTimer);
        countdown = refreshInterval / 1000;
        updateBadge();

        const intervalId = setInterval(updateBadge, 1000);

        refreshTimer = setTimeout(() => {
            clearInterval(intervalId);
            console.log('Refreshing page...');
            window.location.reload();
        }, refreshInterval);
    }

    scheduleRefresh();

    window.addEventListener('beforeunload', () => {
        clearTimeout(refreshTimer);
    });
})();

// Tooltip initialization
document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});