document.addEventListener('DOMContentLoaded', function() {
    const alertTableBody = document.getElementById('alert-table-body');
    const alertCountDisplay = document.getElementById('alert-count-display');
    const notificationSound = document.getElementById('alert-notification-sound');
    const refreshBadge = document.getElementById('refresh-badge');
    const refreshIntervalSeconds = 15;
    const apiURL = '/tier1/api/alerts/';

    let currentFingerprints = new Set();
    let refreshIntervalId = null;
    let countdownIntervalId = null;
    let countdown = refreshIntervalSeconds;

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

    async function fetchAndUpdateAlerts() {
        console.log("Fetching alerts..."); // For debugging
        try {
            const response = await fetch(apiURL);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            const newHtml = data.html;
            const newAlertCount = data.alert_count;
            const newFingerprints = parseFingerprintsFromHTML(newHtml);


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
                alertTableBody.innerHTML = newHtml;
            }
            if (alertCountDisplay) {
                // Update the count text, assuming the format "Total: N"
                alertCountDisplay.textContent = `Total: ${newAlertCount}`;
            }

            // Update current state
            currentFingerprints = newFingerprints;

            // Play sound if new alerts were detected
            if (hasNewAlerts) {
                playNotificationSound();
            }

            // Re-initialize tooltips and event listeners for the new content
            initializeDynamicContent();

        } catch (error) {
            console.error("Failed to fetch or update alerts:", error);
            // Optionally display an error message to the user
        } finally {
            // Reset countdown for the next refresh cycle
            resetCountdown();
        }
    }

    // --- Countdown Timer Logic ---

    function updateCountdownDisplay() {
        if (refreshBadge) {
            refreshBadge.textContent = `Auto-Refresh: ${countdown}s`;
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