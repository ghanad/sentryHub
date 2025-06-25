# SentryHub Internal Metrics Framework Documentation

This document provides an overview of the SentryHub Internal Metrics Framework, how to use it to add new metrics, and example Prometheus alerting rules.

## Objective
The SentryHub Internal Metrics Framework provides a robust, scalable, and centralized solution for generating internal application metrics. It enables developers to easily add metrics for components (e.g., Jira integration, alert processing, database performance) without handling metric formatting, file I/O, or concurrency. Metrics are written to a text file scraped by node_exporter's textfile collector for integration with Prometheus.

## How to Add Metrics

To add a new metric to any part of the SentryHub application:

1.  **Import `metrics_manager`**: At the top of your Python file, import the global `metrics_manager` instance:
    ```python
    from core.services.metrics import metrics_manager
    from django.conf import settings # Also import settings if you need METRICS_ENABLED check
    ```

2.  **Call Metric Methods**: Use `metrics_manager.inc_counter()` for counters or `metrics_manager.set_gauge()` for gauges. Always wrap your metric calls with a check for `settings.METRICS_ENABLED` to ensure metrics are only processed when enabled.

    *   **`inc_counter(name, labels=None, value=1)`**: Increments a counter metric.
        *   `name` (str): The name of the counter (e.g., `sentryhub_jira_api_calls_total`).
        *   `labels` (dict, optional): A dictionary of label key-value pairs (e.g., `{'component': 'jira', 'status': 'success'}`). Labels should be consistent for a given metric name.
        *   `value` (int, optional): The amount to increment the counter by (defaults to 1).

        **Example Usage (Counter)**:
        ```python
        if settings.METRICS_ENABLED:
            metrics_manager.inc_counter(
                'sentryhub_jira_api_calls_total',
                labels={'status': 'success', 'method': 'create_issue'}
            )
        ```

    *   **`set_gauge(name, labels=None, value=0.0)`**: Sets a gauge metric to a specific value.
        *   `name` (str): The name of the gauge (e.g., `sentryhub_component_last_successful_api_call_timestamp`).
        *   `labels` (dict, optional): A dictionary of label key-value pairs.
        *   `value` (float): The value to set the gauge to. For timestamps, use `time.time()`.

        **Example Usage (Gauge)**:
        ```python
        import time
        if settings.METRICS_ENABLED:
            metrics_manager.set_gauge(
                'sentryhub_component_last_successful_api_call_timestamp',
                labels={'component': 'jira'},
                value=time.time()
            )
        ```

## Example Usage from JiraService

The `integrations/services/jira_service.py` file provides a practical example of how metrics are integrated:

*   **Initialization Errors**:
    ```python
    # In JiraService.__init__
    except (JIRAError, ConnectionError, Exception) as jira_init_error:
        logger.error(f"Jira client initialization or connection test failed: {jira_init_error}", exc_info=True)
        self.client = None
        if settings.METRICS_ENABLED:
            metrics_manager.inc_counter(
                'sentryhub_component_initialization_errors_total',
                labels={'component': 'jira'}
            )
    ```

*   **API Call Success/Failure**:
    ```python
    # In JiraService.create_issue (similar logic in add_comment)
    try:
        issue = self.client.create_issue(fields=field_dict)
        if settings.METRICS_ENABLED:
            metrics_manager.inc_counter(
                'sentryhub_jira_api_calls_total',
                labels={'status': 'success', 'method': 'create_issue'}
            )
            metrics_manager.set_gauge(
                'sentryhub_component_last_successful_api_call_timestamp',
                labels={'component': 'jira'},
                value=time.time()
            )
        # ...
    except JIRAError as e:
        if settings.METRICS_ENABLED:
            metrics_manager.inc_counter(
                'sentryhub_jira_api_calls_total',
                labels={'status': 'failure', 'method': 'create_issue'}
            )
        # ...
    ```

## Implemented Metrics

The following metrics are currently implemented:

*   `sentryhub_last_metrics_write_timestamp` (Gauge): Unix timestamp of the last time metrics were successfully written to the file.
*   `sentryhub_component_initialization_errors_total{component="jira"}` (Counter): Incremented when the JiraService fails to initialize or connect.
*   `sentryhub_jira_api_calls_total{status="success", method="..."}` (Counter): Incremented on successful Jira API calls (e.g., `create_issue`, `add_comment`).
*   `sentryhub_jira_api_calls_total{status="failure", method="..."}` (Counter): Incremented on failed Jira API calls.
*   `sentryhub_component_last_successful_api_call_timestamp{component="jira"}` (Gauge): Unix timestamp of the last successful Jira API call.

## Prometheus Alerting Rules

These rules can be added to your Prometheus configuration to monitor the SentryHub Jira integration.

```yaml
groups:
- name: SentryHub.Internal.Jira
  rules:
  - alert: SentryHubMetricsWriteFailure
    expr: time() - sentryhub_last_metrics_write_timestamp > 300
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "SentryHub metrics are not being written"
      description: "The SentryHub application has not written metrics to the textfile collector for over 5 minutes. This indicates a potential issue with the metrics framework or the application itself. Value: {{ $value }}"
      
  - alert: SentryHubJiraIntegrationFailure
    expr: rate(sentryhub_jira_api_calls_total{component="jira", status="failure"}[5m]) > 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "SentryHub is failing to communicate with Jira"
      description: "There are active errors in API calls from SentryHub to Jira. This may prevent ticket creation or updates. Check SentryHub logs for details. Value: {{ $value }}"
  - alert: SentryHubJiraNoRecentSuccess
    expr: time() - sentryhub_component_last_successful_api_call_timestamp{component="jira"} > 3600
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "SentryHub has not had a successful communication with Jira for over 1 hour"
      description: "No successful API calls have been made to Jira recently. This could indicate a silent failure, a network issue, or that no alerts have triggered the Jira integration. Please verify the integration is healthy."