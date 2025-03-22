// Main JavaScript file for SentryHub

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Confirm delete actions
function confirmDelete(event) {
    if (!confirm('Are you sure you want to delete this item?')) {
        event.preventDefault();
    }
}

// Toggle sidebar
function toggleSidebar() {
    document.body.classList.toggle('sidebar-collapsed');
}

// Refresh data periodically (every 30 seconds)
function refreshData() {
    if (document.querySelector('[data-refresh-url]')) {
        fetch(document.querySelector('[data-refresh-url]').dataset.refreshUrl)
            .then(response => response.json())
            .then(data => {
                // Update the content
                document.querySelector('[data-refresh-target]').innerHTML = data.html;
            })
            .catch(error => console.error('Error refreshing data:', error));
    }
}

// Start periodic refresh if needed
if (document.querySelector('[data-refresh-url]')) {
    setInterval(refreshData, 30000);
}

// Handle form submissions with AJAX
document.addEventListener('submit', function(event) {
    if (event.target.hasAttribute('data-ajax')) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);
        
        fetch(form.action, {
            method: form.method,
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                toastr.success(data.message);
                // Optionally redirect or update UI
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            } else {
                // Show error message
                toastr.error(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toastr.error('An error occurred. Please try again.');
        });
    }
}); 