// alerts/static/alerts/js/silence_rule_list.js

document.addEventListener('DOMContentLoaded', function () {
    // Initialize Bootstrap Tooltips if they are used on action buttons or other elements
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Add any other specific JavaScript interactions for this page here.
    // For example, maybe a confirmation before redirecting to the delete page,
    // although the current design uses a separate confirmation page.
    /*
    const deleteButtons = document.querySelectorAll('.delete-rule-btn'); // Add this class to delete buttons if needed
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to proceed to delete this rule?')) {
                event.preventDefault();
            }
        });
    });
    */

    console.log("Silence Rule List JS loaded.");
});