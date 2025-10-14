document.addEventListener('DOMContentLoaded', function() {
    const alertTableBody = document.getElementById('alert-table-body');
    const alertCountDisplay = document.getElementById('alert-count-display');
    const alertModalsContainer = document.getElementById('alert-modals-container');
    const paginationContainer = document.getElementById('alert-pagination');
    const notificationSound = document.getElementById('alert-notification-sound');
    const refreshBadge = document.getElementById('refresh-badge');
    const refreshIntervalSeconds = refreshBadge && refreshBadge.dataset.refreshInterval
        ? parseInt(refreshBadge.dataset.refreshInterval, 10)
        : 15;
    const refreshErrorBanner = document.getElementById('refresh-error-banner');
    const apiURL = window.ALERTS_API_URL;

    let currentFingerprints = new Set();
    let refreshIntervalId = null;
    let countdownIntervalId = null;
    let countdown = refreshIntervalSeconds;
    let isInErrorState = false;

    // --- Helper Functions ---

    function getCurrentFingerprints() {
        const fingerprints = new Set();
        if (alertTableBody) {
            alertTableBody.querySelectorAll('tr[data-fingerprint]').forEach(row => {
                fingerprints.add(row.dataset.fingerprint);
            });
        }
        return fingerprints;
    }

    function parseFingerprintsFromHTML(html) {
        const tempDiv = document.createElement('div');
        // It's safer to wrap table rows in a tbody or table for parsing
        tempDiv.innerHTML = `<table><tbody>${html}</tbody></table>`;
        const fingerprints = new Set();
        tempDiv.querySelectorAll('tr[data-fingerprint]').forEach(row => {
            fingerprints.add(row.dataset.fingerprint);
        });
        return fingerprints;
    }

    function playNotificationSound() {
        if (notificationSound) {
            notificationSound.play().catch(error => {
                // Autoplay might be blocked by the browser if the user hasn't interacted yet
                console.warn("Audio playback failed. User interaction might be required.", error);
                // Optionally, display a visual cue instead or request interaction.
            });
        }
    }

    function initializeDynamicContent() {
        if (!alertTableBody) {
            return;
        }
        // Re-initialize tooltips for new content
        const tooltipTriggerList = [].slice.call(alertTableBody.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            // Ensure old tooltips are disposed if they exist
            const existingTooltip = bootstrap.Tooltip.getInstance(tooltipTriggerEl);
            if (existingTooltip) {
                existingTooltip.dispose();
            }
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Re-attach event listeners for expand/collapse buttons within the table body
        alertTableBody.querySelectorAll('.expand-btn').forEach(btn => {
            // Remove potential old listeners if needed, though replacing innerHTML usually handles this
            btn.addEventListener('click', handleExpandCollapseClick);
        });

        // Re-attach event listeners for row clicks within the table body
        alertTableBody.querySelectorAll('.alert-row').forEach(row => {
            // Remove potential old listeners if needed
            row.addEventListener('click', handleRowClick);
        });
    }

    // --- Event Handlers (for dynamic content) ---

    function handleExpandCollapseClick(e) {
        e.stopPropagation();
        const icon = this.querySelector('i');
        if (icon) {
            icon.classList.toggle('bx-chevron-right');
            icon.classList.toggle('bx-chevron-down');
        }
        // Ensure the collapse target is correctly toggled (Bootstrap handles this via data attributes)
    }

    function handleRowClick(e) {
        // Prevent expansion if clicking on a link or button within the row
        if (e.target.tagName === 'A' || e.target.closest('a') || e.target.closest('button')) return;

        const expandBtn = this.querySelector('.expand-btn');
        if (expandBtn) {
            e.stopPropagation(); // Prevent triggering multiple times if nested
            // Find the associated collapse element and toggle it manually or trigger the button click
            const targetId = expandBtn.getAttribute('data-bs-target');
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                 // Use Bootstrap's Collapse instance to toggle
                 const collapseInstance = bootstrap.Collapse.getOrCreateInstance(targetElement);
                 collapseInstance.toggle();
                 // Also update the icon state if the button wasn't clicked directly
                 const icon = expandBtn.querySelector('i');
                 if (icon) {
                     icon.classList.toggle('bx-chevron-right');
                     icon.classList.toggle('bx-chevron-down');
                 }
            } else {
                 // Fallback: click the button if target not found easily
                 expandBtn.click();
            }
        }
    }


    // --- Core Refresh Logic ---

    function buildFetchURL() {
        try {
            const requestUrl = new URL(apiURL, window.location.origin);
            const currentParams = new URLSearchParams(window.location.search);
            currentParams.forEach((value, key) => {
                requestUrl.searchParams.set(key, value);
            });
            return requestUrl.toString();
        } catch (error) {
            console.error('Failed to build request URL', error);
            return apiURL;
        }
    }

    async function fetchAndUpdateAlerts() {
        console.log("Fetching alerts..."); // For debugging
        try {
            const response = await fetch(buildFetchURL(), {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            const rowsHtml = data.rows_html;
            const newAlertCount = data.alert_count;
            const newFingerprints = parseFingerprintsFromHTML(rowsHtml);


            // Detect new alerts
            let hasNewAlerts = false;
            newFingerprints.forEach(fp => {
                if (!currentFingerprints.has(fp)) {
                    hasNewAlerts = true;
                    // No need to check further once one new alert is found
                }
            });

            // Update DOM
            if (alertTableBody) {
                alertTableBody.innerHTML = rowsHtml;
            }
            if (alertCountDisplay) {
                // Update the count text, assuming the format "Total: N"
                alertCountDisplay.textContent = `Total: ${newAlertCount}`;
            }
            if (alertModalsContainer) {
                alertModalsContainer.innerHTML = data.modals_html;
            }
            if (paginationContainer) {
                paginationContainer.innerHTML = data.pagination_html;
            }

            // Update current state
            currentFingerprints = newFingerprints;

            // Play sound if new alerts were detected
            if (hasNewAlerts) {
                playNotificationSound();
            }

            // Re-initialize tooltips and event listeners for the new content
            initializeDynamicContent();

            // Clear any previous error message and styling once data loads
            isInErrorState = false;
            if (refreshErrorBanner) {
                refreshErrorBanner.classList.add('d-none');
                refreshErrorBanner.removeAttribute('data-error');
                refreshErrorBanner.textContent = '';
            }

        } catch (error) {
            console.error("Failed to fetch or update alerts:", error);
            isInErrorState = true;

            if (refreshErrorBanner) {
                const errorTime = new Date().toLocaleTimeString();
                refreshErrorBanner.classList.remove('d-none');
                const baseMessage = 'Unable to refresh alerts. The system will keep retrying automatically.';
                const detailMessage = error && error.message ? ` (${error.message})` : '';
                refreshErrorBanner.textContent = `${baseMessage}${detailMessage} Last attempt: ${errorTime}.`;
                refreshErrorBanner.setAttribute('data-error', 'true');
            }
        } finally {
            // Reset countdown for the next refresh cycle
            resetCountdown();
        }
    }

    // --- Countdown Timer Logic ---

    function updateCountdownDisplay() {
        if (refreshBadge) {
            if (isInErrorState) {
                refreshBadge.textContent = `Retrying in ${countdown}s`;
                refreshBadge.classList.remove('bg-secondary');
                refreshBadge.classList.add('bg-danger');
            } else {
                refreshBadge.textContent = `Auto-Refresh: ${countdown}s`;
                refreshBadge.classList.remove('bg-danger');
                refreshBadge.classList.add('bg-secondary');
            }
        }
        countdown--;

        if (countdown < 0) {
            clearInterval(countdownIntervalId); // Stop this countdown
            // Check visibility before fetching
            if (document.visibilityState === 'visible') {
                 fetchAndUpdateAlerts(); // This will reset the countdown upon completion/error
            } else {
                 console.log("Tab not visible, delaying refresh.");
                 // Reset countdown and check again after interval without fetching
                 resetCountdown();
            }
        }
    }

    function startCountdown() {
        // Clear any existing interval first
        if (countdownIntervalId) {
            clearInterval(countdownIntervalId);
        }
        countdown = refreshIntervalSeconds; // Reset timer
        updateCountdownDisplay(); // Update immediately
        countdownIntervalId = setInterval(updateCountdownDisplay, 1000); // Update every second
    }

    function resetCountdown() {
         startCountdown(); // Simply restart the countdown process
    }

    // --- Initialization ---

    // Initial population of fingerprints
    currentFingerprints = getCurrentFingerprints();

    // Initialize dynamic content listeners for initially loaded content
    initializeDynamicContent();

    // Start the refresh cycle
    if (alertTableBody) { // Only start if the table exists
        startCountdown();
    } else {
        console.warn("Alert table body not found. Auto-refresh disabled.");
    }

    // Optional: Add logic to pause refresh on interaction (e.g., modal open) if desired
    // Optional: Add logic to handle browser visibility changes more robustly

});