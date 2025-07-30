document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Tab handling with URL update
    const alertTabs = document.getElementById('alertTabs');
    if (alertTabs) {
        alertTabs.addEventListener('shown.bs.tab', function (event) {
            const activeTab = event.target.getAttribute('aria-controls');
            const newUrl = `${window.location.pathname}?tab=${activeTab}`;
            window.history.replaceState(null, null, newUrl);
        });

        // Check for tab parameter in URL on load
        const urlParams = new URLSearchParams(window.location.search);
        const tabParam = urlParams.get('tab');
        if (tabParam) {
            const tabButton = document.querySelector(`#${tabParam}-tab`);
            if (tabButton) {
                bootstrap.Tab.getOrCreateInstance(tabButton).show();
            }
        }
    }

    // Silence button handler - kept for compatibility
    const silenceButton = document.querySelector('.card-body .btn-silence');
    if (silenceButton) {
        silenceButton.addEventListener('click', function(event) {
            console.log('Silence button clicked in detail view, redirecting to create form with labels.');
        });
    }

    // Duration calculation functions (used by history tab)
    function calculateAndDisplayDurations() {
        document.querySelectorAll('[data-start-time]').forEach(element => {
            const startTime = new Date(element.dataset.startTime);
            const endTime = element.dataset.endTime ? 
                new Date(element.dataset.endTime) : 
                new Date();

            const durationMs = endTime - startTime;
            element.textContent = formatDuration(durationMs);
        });
    }

    function formatDuration(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) {
            return `${days}d ${hours % 24}h`;
        } else if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }

    // Run duration calculations on load
    calculateAndDisplayDurations();

    // Apply RTL/LTR handling for documentation sections similar to docs page
    document.querySelectorAll('.documentation-content').forEach(section => {
        // Detect direction for standard block elements
        section.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, blockquote, div').forEach(el => {
            const dirAttr = el.getAttribute('dir');
            if (dirAttr === 'rtl') {
                el.style.direction = 'rtl';
                el.style.textAlign = 'right';
                el.classList.add('rtl-text');
            } else if (dirAttr === 'ltr') {
                el.style.direction = 'ltr';
                el.style.textAlign = 'left';
                el.classList.remove('rtl-text');
            } else if (typeof setTextDirection === 'function') {
                setTextDirection(el);
            }
        });

        // Force LTR for code blocks
        section.querySelectorAll('pre, code, kbd, samp').forEach(el => {
            el.setAttribute('dir', 'ltr');
            el.style.direction = 'ltr';
            el.style.textAlign = 'left';
        });
    });
});

// Function to update tab content if needed (called from included JS files)
function updateAlertTabContent(content) {
    const activeTabPane = document.querySelector('.tab-pane.active');
    if (activeTabPane) {
        activeTabPane.innerHTML = content;
        // Re-init any necessary JS
        if (typeof initComments !== 'undefined') {
            initComments();
        }
    }
}
