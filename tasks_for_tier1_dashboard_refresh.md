# Plan for Enhancing /tier1/unacked Dashboard

## Description

The `/tier1/unacked` dashboard currently requires manual refresh to update the list of unacknowledged alerts. This is not ideal as users might miss critical alerts if they are not actively refreshing the page. Additionally, there is no indication of connection status or any form of alert notification.

This plan aims to enhance the dashboard by implementing real-time updates, sound alerts, browser notifications, and a connection status indicator. These changes will ensure users are promptly notified of new alerts and can rely on the dashboard for accurate, up-to-date information without manual intervention.

## Changes

1.  **Real-Time Updates via WebSockets:** Instead of manual page refreshes, the dashboard will use WebSockets to receive updates from the server in real-time.
2.  **Sound Alerts:** A sound alert will be played when a new alert is received, ensuring that users are immediately aware of critical issues.
3.  **Browser Notifications:** Browser notifications will be used to alert users even when they are not actively on the dashboard tab.
4.  **Connection Status Indicator:** A visual indicator will be added to the UI to show whether the WebSocket connection is active or not.
5. **Improved Error Handling**: Implemented error handling and automatic reconnection when connection lost.
6. **Comprehensive Testing**: Write Unit and functional test to make sure everything work correctly.

## Subtasks

- [x] **Establish WebSocket Connection:**
    - [x] Establish a WebSocket connection between the browser and the server.
    - [x] Handle connection open, close, and error events.
Note: The `tier1_dashboard/static/tier1_dashboard/js/unack_alerts.js` file was modified to establish a WebSocket connection and handle related events.
- [x] **Server-Side Alert Updates:**
    - [x] Modify the server-side code to push alert updates to connected clients via WebSockets.
Note: The `alerts/consumers.py` and `alerts/routing.py` files were added. The `sentryHub/asgi.py` and `alerts/services/alerts_processor.py` files were modified to enable sending alerts to clients via WebSockets.
- [x] **Client-Side Data Handling:**
    - [x] Implement client-side logic to receive and process WebSocket messages.
    - [x] Update the UI with new alert data without a full page refresh.
- [x] **Sound Alerts:**
    - [x] Trigger sound alerts on the client-side when new alerts arrive.
    - [x] Allow users to toggle sound alerts on/off.
- [x] **Browser Notifications:**
    - [x] Request permission for browser notifications.
    - [x] Send browser notifications for new alerts.
    - [x] Allow users to toggle browser notifications on/off.
- [x] **Connection Status Indicator:**
    - [x] Add a visual indicator (e.g., icon) to show the connection status.
    - [x] Update the indicator based on WebSocket connection state.
- [x] **Error Handling:**
    - [x] Implement proper error handling on both client and server.
    - [x] Attempt to re-establish a closed connection.
- [x] **Testing:**
    - [x] Write unit and functional tests for the new changes.
Note: The `alerts/tests/test_consumers.py` and `alerts/tests/test_alerts_processor.py` files were created and added unit test for AlertConsumer, process_alert and resolve_alert.

Note: The `tier1_dashboard/static/tier1_dashboard/js/unack_alerts.js` file was modified to handle incoming messages from the server and update the UI.
Note: The `tier1_dashboard/static/tier1_dashboard/js/unack_alerts.js` and `tier1_dashboard/templates/tier1_dashboard/unack_alerts.html` files were modified to enable sound alert and add toggle to turn it on/off.
Note: The `tier1_dashboard/static/tier1_dashboard/js/unack_alerts.js` and `tier1_dashboard/templates/tier1_dashboard/unack_alerts.html` files were modified to enable browser notification and add toggle to turn it on/off.
Note: The `tier1_dashboard/static/tier1_dashboard/js/unack_alerts.js` and `tier1_dashboard/templates/tier1_dashboard/unack_alerts.html` files were modified to add the connection status indicator.
Note: The `alerts/consumers.py` file was modified to add more error handling.

## Post-Implementation Fixes

- [x] **Fix Sound/Notification Functionality:**
    - [x] Investigate toggle event handlers in `unack_alerts.js`
    - [x] Ensure sound plays when enabled (added robust error handling)
    - [x] Validate notification permissions persistence (logic adjusted in JS)
    - [x] Add fallback for missing sound file
    Note: Updated `tier1_dashboard/static/tier1_dashboard/js/unack_alerts.js` with improved sound handling

- [x] **Checkbox UI/UX Improvements:**
    - [x] Redesign checkbox layout using toggle switches
    - [x] Implement consistent hover/focus states
    - [x] Add visual feedback on toggle
    Note: Modified `tier1_dashboard/static/tier1_dashboard/css/unack_alerts.css` and `tier1_dashboard/templates/tier1_dashboard/unack_alerts.html`

- [x] **Default Enabled States:**
    - [x] Set `checked` attribute on checkbox inputs
    - [x] Verify initial state consistency after page reload (logic adjusted in JS)
    Note: Updated `tier1_dashboard/templates/tier1_dashboard/unack_alerts.html`

- [ ] **Validation Testing:**
    - [ ] Create test matrix for all toggle combinations
    - [ ] Verify cross-browser behavior
    - [ ] Add Cypress end-to-end tests