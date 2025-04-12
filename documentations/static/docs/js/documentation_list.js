// docs/static/docs/js/documentation_list.js

document.addEventListener('DOMContentLoaded', function () {
    // Initialize Bootstrap Tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Add any other specific JavaScript interactions for this page here.
    // e.g., delete confirmation for documentation items.
    /*
    const deleteButtons = document.querySelectorAll('.delete-doc-btn'); // Add class to delete buttons
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to delete this documentation? This cannot be undone.')) {
                event.preventDefault();
            }
        });
    });
    */

    console.log("Documentation List JS loaded.");
});