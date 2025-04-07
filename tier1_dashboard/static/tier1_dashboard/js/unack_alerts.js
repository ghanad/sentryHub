document.addEventListener('DOMContentLoaded', function() {
    // Handle row clicks for expansion
    document.querySelectorAll('.alert-row').forEach(row => {
        row.addEventListener('click', function(e) {
            if (e.target.tagName === 'A' || e.target.closest('a') || e.target.closest('button')) return;
            const expandBtn = this.querySelector('.expand-btn');
            if (expandBtn) {
                e.stopPropagation();
                expandBtn.click();
            }
        });
    });

    // Handle expand/collapse buttons
    const expandButtons = document.querySelectorAll('.expand-btn');
    expandButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const icon = this.querySelector('i');
            if (icon) {
                icon.classList.toggle('bx-chevron-right');
                icon.classList.toggle('bx-chevron-down');
            }
        });
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});