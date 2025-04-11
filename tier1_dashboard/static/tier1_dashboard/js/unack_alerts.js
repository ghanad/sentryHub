document.addEventListener('DOMContentLoaded', function() {
    const alertTableBody = document.getElementById('alert-table-body');
    const alertCountDisplay = document.getElementById('alert-count-display');
    const notificationSound = document.getElementById('alert-notification-sound');
    let soundErrorLogged = false; // Track if we've logged sound errors
    const refreshBadge = document.getElementById('refresh-badge');
    const refreshIntervalSeconds = 15;
    const apiURL = window.ALERTS_API_URL;
    const websocketURL = 'ws://sentryhub_web:8000/alerts/ws/';
    const soundToggle = document.getElementById('sound-toggle');
    const notificationToggle = document.getElementById('notification-toggle');
    let soundEnabled = soundToggle ? soundToggle.checked : true; // Initialize based on default HTML state
    let notificationEnabled = notificationToggle ? notificationToggle.checked : true; // Initialize based on default HTML state

    let currentFingerprints = new Set();
    let refreshIntervalId = null;
    let countdownIntervalId = null;
    let countdown = refreshIntervalSeconds;
    let websocket;
    let isWebSocketConnected = false;

    // --- Connection Status Indicator ---
    const connectionStatus = document.getElementById('connection-status');
    function updateConnectionStatus(isConnected) {
        connectionStatus.classList.toggle('connected', isConnected);
        connectionStatus.classList.toggle('disconnected', !isConnected);
    }

    // --- Sound Toggle ---
    if (soundToggle) {
        soundToggle.addEventListener('change', () => soundEnabled = soundToggle.checked);
    }

    // --- Notification Toggle & Permissions ---
    if (notificationToggle) {
        notificationToggle.addEventListener('change', handleNotificationToggleChange);
    }
    requestNotificationPermissionAndUpdateToggle(); // Request permission on load

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

    function initializeWebSocket() {
        websocket = new WebSocket(websocketURL);

        websocket.onopen = function(event) {
            isWebSocketConnected = true;
            console.log("WebSocket connected");
            updateConnectionStatus(true);
        };

        websocket.onclose = function(event) {
            isWebSocketConnected = false;
            console.log("WebSocket disconnected:", event);
            updateConnectionStatus(false);
            setTimeout(initializeWebSocket, 3000);
        };

        websocket.onerror = function() {
            isWebSocketConnected = false;
            console.error("WebSocket error");
         };

        websocket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log("Received WebSocket message:", data);
                if (data && data.alerts) {
                    updateAlertTable(data.alerts);
                }
            } catch (error) {
                console.error("Error parsing WebSocket message:", error);
            }
        };
    }

    // --- Browser Notifications ---
    // Event listener moved up near initialization

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
                if (soundEnabled) {
                    try {
                        playSound();
                    } catch (error) {
                        if (!soundErrorLogged) {
                            console.error("Error playing sound:", error);
                            soundErrorLogged = true;
                        }
                    }
                }
                const alertMessage = `New alert received! Check the dashboard for details.`;
                sendNotification(alertMessage); // sendNotification now checks internally
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

    initializeWebSocket();

    // --- Browser Notification Functions ---
    function requestNotificationPermissionAndUpdateToggle() {
        if (!('Notification' in window)) {
            console.warn("This browser does not support desktop notification");
            if (notificationToggle) notificationToggle.disabled = true; // Disable toggle if not supported
            notificationEnabled = false;
            return;
        }

        if (Notification.permission === 'granted') {
            // Permission already granted, ensure toggle reflects internal state
            if (notificationToggle) notificationEnabled = notificationToggle.checked;
        } else if (Notification.permission !== 'denied') {
            // Ask for permission
            Notification.requestPermission().then(permission => {
                console.log("Notification permission:", permission);
                if (permission === 'granted') {
                    // Update internal state based on toggle *after* getting permission
                    if (notificationToggle) notificationEnabled = notificationToggle.checked;
                } else {
                    // Permission denied or dismissed
                    notificationEnabled = false;
                    if (notificationToggle) notificationToggle.checked = false; // Uncheck toggle if denied
                }
            });
        } else {
            // Permission was explicitly denied previously
            notificationEnabled = false;
            if (notificationToggle) notificationToggle.checked = false; // Ensure toggle is off
            if (notificationToggle) notificationToggle.disabled = true; // Optionally disable if permanently denied
        }
    }

    function playSound() {
        try {
            // Try playing the configured sound
            notificationSound.currentTime = 0; // Rewind to start
            notificationSound.play().catch(error => {
                if (!soundErrorLogged) {
                    console.error("Sound playback failed:", error);
                    soundErrorLogged = true;
                }
            });
        } catch (error) {
            if (!soundErrorLogged) {
                console.error("Sound error:", error);
                soundErrorLogged = true;
            }
        }
    }

    function sendNotification(message) {
        // Send only if toggle is checked AND permission is granted
        if (notificationEnabled && Notification.permission === 'granted') {
            new Notification('New Alert', { body: message });
        }
    }

    // Initialize dynamic content listeners for initially loaded content
    initializeDynamicContent();

    // Handle notification toggle changes *after* initial permission check
    function handleNotificationToggleChange() {
        notificationEnabled = notificationToggle.checked;
        // If user tries to enable without permission, re-request
        if (notificationEnabled && Notification.permission !== 'granted') {
            console.log("Requesting notification permission due to toggle change...");
            requestNotificationPermissionAndUpdateToggle();
        }
    }

    // Start the refresh cycle
    if (alertTableBody) { // Only start if the table exists
        startCountdown();
    } else {
        console.warn("Alert table body not found. Auto-refresh disabled.");
    }

    // Optional: Add logic to pause refresh on interaction (e.g., modal open) if desired
    // Optional: Add logic to handle browser visibility changes more robustly
});