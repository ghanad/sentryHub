// Path: tier1_dashboard/static/tier1_dashboard/js/tier1_dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    const alertTableBody = document.getElementById('alert-table-body');
    const noAlertsMessage = document.getElementById('no-alerts-message');
    const statusIndicator = document.getElementById('connection-status');
    const lastUpdatedElement = document.getElementById('last-updated-time');

    const acknowledgeModalEl = document.getElementById('acknowledgeModal');
    const acknowledgeModal = new bootstrap.Modal(acknowledgeModalEl);
    const acknowledgeForm = document.getElementById('acknowledgeForm');
    const ackAlertNameEl = document.getElementById('ack-alert-name');
    const ackAlertFingerprintInput = document.getElementById('ack-alert-fingerprint');
    const ackCommentTextarea = document.getElementById('id_comment');

    let connectionErrorOccurred = false;
    let lastSuccessfulUpdate = null;
    const REFRESH_INTERVAL = 30000; // 30 seconds
    const API_URL = '/tier1/api/alerts/'; // Replaced Django URL tag

    function refreshAlerts() {
        statusIndicator.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';

        fetch(API_URL)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // 1. Update Table Content
                alertTableBody.innerHTML = data.html;
                if (data.alert_count > 0) {
                    noAlertsMessage.classList.add('d-none');
                } else {
                    noAlertsMessage.classList.remove('d-none');
                }

                // 2. Update Status Indicator
                statusIndicator.innerHTML = '<i class="bx bx-check-circle text-success"></i> Live';
                statusIndicator.classList.remove('error', 'bg-danger', 'text-white');
                statusIndicator.classList.add('connected', 'bg-light', 'text-dark');
                lastSuccessfulUpdate = new Date(data.timestamp);
                lastUpdatedElement.textContent = lastSuccessfulUpdate.toLocaleTimeString();

                // 3. Reset error flag
                connectionErrorOccurred = false;

                // 4. Re-initialize tooltips for new content
                var tooltipTriggerList = [].slice.call(alertTableBody.querySelectorAll('[data-bs-toggle="tooltip"]'))
                var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
                    return new bootstrap.Tooltip(tooltipTriggerEl)
                });
            })
            .catch(error => {
                console.error('Error fetching alerts:', error);
                // 1. Update Status Indicator to Error state
                statusIndicator.innerHTML = '<i class="bx bx-error-circle text-white"></i> Connection Error';
                statusIndicator.classList.remove('connected', 'bg-light', 'text-dark');
                statusIndicator.classList.add('error', 'bg-danger', 'text-white');
                // Keep last successful update time visible
                if (lastSuccessfulUpdate) {
                    lastUpdatedElement.textContent = lastSuccessfulUpdate.toLocaleTimeString() + " (failed)";
                } else {
                    lastUpdatedElement.textContent = "Never (failed)";
                }

                // 2. Show notification only on the first error
                if (!connectionErrorOccurred) {
                    SentryNotification.error('Failed to refresh alerts. Data might be stale.', { timeOut: 10000, preventDuplicates: false });
                    connectionErrorOccurred = true;
                }
            });
    }

    // --- Acknowledge Modal Handling ---
    // Use event delegation on the table body
    alertTableBody.addEventListener('click', function(event) {
        const button = event.target.closest('.ack-button');
        if (button) {
            const fingerprint = button.dataset.alertFingerprint;
            const name = button.dataset.alertName;
            ackAlertNameEl.textContent = name;
            ackAlertFingerprintInput.value = fingerprint;
            ackCommentTextarea.value = ''; // Clear previous comment
        }
    });

    acknowledgeForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const fingerprint = ackAlertFingerprintInput.value;
        const comment = ackCommentTextarea.value.trim();

        if (!comment) {
            SentryNotification.warning('Please enter a comment for acknowledgement.');
            ackCommentTextarea.focus();
            return;
        }

        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', this.querySelector('[name=csrfmiddlewaretoken]').value);
        formData.append('comment', comment);
        formData.append('acknowledged', 'true');

        const ackButton = this.querySelector('button[type="submit"]');
        const originalButtonText = ackButton.innerHTML;
        ackButton.disabled = true;
        ackButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Acknowledging...';

        const acknowledgeUrl = `/api/v1/alerts/${fingerprint}/acknowledge/`;

        fetch(acknowledgeUrl, {
            method: 'PUT',
            body: JSON.stringify({ comment: comment, acknowledged: true }),
            headers: {
                'X-CSRFToken': this.querySelector('[name=csrfmiddlewaretoken]').value,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.detail || `Acknowledgement failed with status ${response.status}`);
                }).catch(() => {
                    throw new Error(`Acknowledgement failed with status ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            SentryNotification.success('Alert acknowledged successfully!');
            acknowledgeModal.hide();
            refreshAlerts();
        })
        .catch(error => {
            console.error('Acknowledgement error:', error);
            SentryNotification.error(`Failed to acknowledge alert: ${error.message}`);
        })
        .finally(() => {
            ackButton.disabled = false;
            ackButton.innerHTML = originalButtonText;
        });
    });

    // --- Initial Load & Interval ---
    refreshAlerts(); // Initial load
    setInterval(refreshAlerts, REFRESH_INTERVAL);
});
