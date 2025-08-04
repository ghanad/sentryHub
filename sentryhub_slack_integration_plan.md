# SentryHub Slack Notification Integration Plan (Using Nginx Reverse Proxy)

This document outlines the step-by-step plan to integrate a Slack notification feature into the SentryHub project. The architecture is designed for security and scalability by using Nginx as a reverse proxy. This approach decouples the main application from the external service details and centralizes outbound traffic management.

The Django application will send notifications to an internal Nginx endpoint, which will then securely proxy the request to the actual Slack Webhook URL. Celery will be used for asynchronous task processing.

## Step 1: Configure Nginx as a Reverse Proxy

🎯 **Goal:**  
To set up Nginx on the proxy server to act as a secure gateway, forwarding requests from SentryHub to the real Slack Webhook URL. This keeps the secret webhook URL out of the Django application's configuration.

🛠️ **Tasks:**  
- On your proxy server, create a new Nginx configuration file (e.g., `/etc/nginx/conf.d/sentryhub_proxy.conf`).  
- Define a server block to listen for requests from your SentryHub application.  
- Inside the server block, create a location for the Slack proxy (e.g., `/slack-proxy/`).  
- Use the `proxy_pass` directive within the location block to forward requests to the actual Slack Webhook URL.  
- Add necessary `proxy_set_header` directives to ensure the request is correctly formatted for Slack.  
- (Optional but Recommended) Implement rate limiting to prevent flooding the Slack channel.  
- Reload the Nginx configuration to apply the changes.

## Step 2: Centralized Configuration in Django

🎯 **Goal:**  
To configure the SentryHub application to send requests to the newly created internal Nginx endpoint instead of the direct Slack URL.

🛠️ **Tasks:**  
- Locate the main settings file at `sentryHub/settings.py`.  
- Define a new setting, `SLACK_INTERNAL_ENDPOINT`, which holds the full URL to the Nginx proxy location (e.g., `http://<your-nginx-server-ip>/slack-proxy/`).  
- Ensure this setting is sourced from an environment variable for flexibility.  
- **Note:** The `PROXY_CONFIG` dictionary is no longer needed for this feature, as Django will not be handling proxy logic directly.

## Step 3: Database Model for Notification Rules

🎯 **Goal:**  
To create a database model that will store the rules for sending Slack notifications. This allows administrators to define which alerts should be sent to which Slack channels.

🛠️ **Tasks:**  
- Edit `integrations/models.py`.  
- Create a model named `SlackIntegrationRule`.  
- This model should include the following fields:  
  - `name`: A unique and descriptive name for the rule.  
  - `is_active`: A boolean to enable or disable the rule.  
  - `priority`: An integer to resolve conflicts (higher value = higher priority).  
  - `match_criteria`: A `JSONField` to define the alert labels that trigger this rule.  
  - `slack_channel`: The destination Slack channel (e.g., `#critical-alerts`).  
  - `message_template`: A text field for the Slack message content, supporting Django Template Language syntax.  
- Set the model’s default ordering to be based on priority.

## Step 4: Slack Communication Service

🎯 **Goal:**  
To encapsulate all the logic for sending messages into a single, reusable service class. This service will now send requests to the internal Nginx endpoint.

🛠️ **Tasks:**  
- Create a new file: `integrations/services/slack_service.py`.  
- Define a class named `SlackService`.  
- The `__init__` method should read the `SLACK_INTERNAL_ENDPOINT` from the Django settings.  
- Create a primary method `send_notification(channel, message)`.  
- Inside this method, use the `requests` library to send a `POST` request to the internal Nginx endpoint URL.  
- The `proxies` argument is not needed in the `requests.post()` call.  
- Implement robust error handling for `requests.exceptions.RequestException` to manage potential issues with the connection to Nginx.

## Step 5: Asynchronous Task for Sending Notifications

🎯 **Goal:**  
To create a Celery task that handles rendering the message template and sending the notification asynchronously, preventing any blocking in the main application.

🛠️ **Tasks:**  
- Edit `integrations/tasks.py`.  
- Define a new Celery task named `process_slack_for_alert_group` that accepts `alert_group_id` and `rule_id`.  
- Inside the task, perform the following steps:  
  - Fetch the `AlertGroup` and `SlackIntegrationRule` objects from the database.  
  - Gather all necessary context variables (labels, annotations, etc.) for the message template.  
  - Render the final message string from the `message_template` field of the rule.  
  - Instantiate the `SlackService`.  
  - Call the `send_notification` method of the service, passing the channel from the rule and the rendered message.

## Step 6: Rule Matching Service

🎯 **Goal:**  
To build a service that finds the best `SlackIntegrationRule` for a given alert based on its labels, keeping the matching logic separate and reusable.

🛠️ **Tasks:**  
- Create a new file: `integrations/services/slack_matcher.py`.  
- Define a class `SlackRuleMatcherService` (following the pattern of `JiraRuleMatcherService`).  
- Create a method `find_matching_rule(alert_labels)` that:  
  - Retrieves all active `SlackIntegrationRule` objects.  
  - Filters rules where `match_criteria` is a complete subset of the `alert_labels`.  
  - Selects the single best rule based on the highest priority, using the rule name as a tie-breaker.  
  - Returns the matched rule object or `None` if no rules match.

## Step 7: Signal Handler for Integration

🎯 **Goal:**  
To trigger the Slack notification workflow whenever an alert is processed by listening to the `alert_processed` signal.

🛠️ **Tasks:**  
- Edit `integrations/handlers.py`.  
- Create a new signal receiver function for the `alert_processed` signal.  
- Inside this handler, implement the logic to:  
  - Check if the alert's status is `firing` and it is not silenced.  
  - If the conditions are met, use the `SlackRuleMatcherService` to find a matching rule.  
  - If a rule is found, dispatch the `process_slack_for_alert_group` Celery task with the required `alert_group_id` and `rule_id`.

## Step 8: User Interface and Admin Integration

🎯 **Goal:**  
To provide administrators with a user-friendly interface to manage Slack notification rules.

🛠️ **Tasks:**  

**Admin Panel:**  
- Register the `SlackIntegrationRule` model in `integrations/admin.py` for basic management via the Django admin.

**Web UI (CRUD):**  
- Create a full set of views (`ListView`, `CreateView`, `UpdateView`, `DeleteView`) in `integrations/views.py` for `SlackIntegrationRule`.  
- Add the corresponding URL patterns to `integrations/urls.py`.  
- Create the HTML templates (`list`, `form`, `confirm_delete`) in the `integrations/templates/integrations/` directory, matching the style and structure of the existing Jira rule pages.