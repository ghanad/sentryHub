// Path: admin_dashboard/static/admin_dashboard/js/admin.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Date range filter functionality
    const dateFrom = document.getElementById('date_from');
    const dateTo = document.getElementById('date_to');

    if (dateFrom && dateTo) {
        dateFrom.addEventListener('change', function() {
            if (dateTo.value && new Date(dateFrom.value) > new Date(dateTo.value)) {
                dateTo.value = dateFrom.value;
            }
        });

        dateTo.addEventListener('change', function() {
            if (dateFrom.value && new Date(dateTo.value) < new Date(dateFrom.value)) {
                dateFrom.value = dateTo.value;
            }
        });
    }

    // Handle comment deletion - for future functionality
    const deleteButtons = document.querySelectorAll('.delete-comment-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this comment?')) {
                e.preventDefault();
            }
        });
    });

    // Toggle sidebar on mobile
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function() {
            document.querySelector('.admin-sidebar').classList.toggle('show');
        });
    }

    // Admin notification system
    function showAdminNotification(message, type = 'info') {
        // Check if toastr is available
        if (typeof toastr !== 'undefined') {
            toastr[type](message);
        } else {
            alert(message);
        }
    }

    // Example of using the notification system
    // Uncomment to test
    // showAdminNotification('Welcome to the admin dashboard', 'success');

    // Handle bulk actions if implemented
    const bulkActionForm = document.getElementById('bulkActionForm');
    if (bulkActionForm) {
        bulkActionForm.addEventListener('submit', function(e) {
            const action = document.getElementById('bulkAction').value;
            const selected = document.querySelectorAll('input[name="selected_items"]:checked');

            if (selected.length === 0) {
                e.preventDefault();
                showAdminNotification('Please select at least one item', 'warning');
            } else if (action === 'delete' && !confirm(`Are you sure you want to delete ${selected.length} selected items?`)) {
                e.preventDefault();
            }
        });
    }
});