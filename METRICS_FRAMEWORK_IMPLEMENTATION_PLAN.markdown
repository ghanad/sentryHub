# SentryHub Internal Metrics Framework

## Objective
The SentryHub Internal Metrics Framework provides a robust, scalable, and centralized solution for generating internal application metrics. It enables developers to easily add metrics for components (e.g., Jira integration, alert processing, database performance) without handling metric formatting, file I/O, or concurrency. Metrics are written to a text file scraped by node_exporter's textfile collector for integration with Prometheus.

## Architectural Design
The framework is built on the following principles:
- **Decoupling**: Business logic (e.g., JiraService) is unaware of Prometheus text format or file operations, only signaling events.
- **Centralization**: A singleton `MetricManager` service aggregates and persists all metrics for consistency and maintainability.
- **Performance**: Metrics are aggregated in memory and periodically written to the file system by a background task to minimize I/O overhead.
- **Atomicity**: File writes use a temporary file and `os.rename` for atomic operations, preventing node_exporter from scraping incomplete data.
- **Scalability**: The framework supports extensible metric types (Counters, Gauges, etc.) and new components.

### High-Level Workflow
1. An application event occurs (e.g., a failed Jira API call).
2. The code calls a method on the global `MetricManager` instance (e.g., `metrics_manager.inc_counter()`).
3. `MetricManager` updates its in-memory metric registry.
4. A Celery Beat task triggers `metrics_manager.write_metrics()` every 15 seconds.
5. `write_metrics()` formats metrics into Prometheus text format and atomically writes to the designated file.
6. `node_exporter` scrapes the file, and Prometheus ingests the metrics.

### System Diagram
```mermaid
graph TD
    subgraph "SentryHub Application (Django/Celery)"
        A[Business Logic e.g., JiraService] -->|metrics_manager.inc_counter()| B(MetricManager Service - Singleton);
        B --> C[In-Memory Metric Registry];
        D[Celery Beat Task (every 15s)] -->|calls| E[MetricManager.write_metrics()];
        E --> F[Atomic File Write];
    end
    subgraph "Monitoring Infrastructure"
        F --> G["metrics.prom File"];
        H[node_exporter] --Scrapes--> G;
        I[Prometheus] --Scrapes--> H;
        I --> J[Alertmanager];
    end
```

## Implementation Tasks
The following tasks outline the steps to implement the metrics framework.

### Task 1: Project Configuration
**Goal**: Configure settings in `sentryHub/settings.py` for the framework.

**Steps**:
- Add settings for the Internal Metrics Framework.
- Define:
  - `METRICS_ENABLED`: Boolean to enable/disable the framework (default: `True`).
  - `METRICS_FILE_PATH`: Absolute path for the metrics file (e.g., `/var/lib/node_exporter/textfile_collector/sentryhub.prom`).

**Example**:
```python
# sentryHub/settings.py
METRICS_ENABLED = os.environ.get('SENTRYHUB_METRICS_ENABLED', 'True').lower() == 'true'
METRICS_FILE_PATH = os.environ.get('SENTRYHUB_METRICS_FILE_PATH', "/var/lib/node_exporter/textfile_collector/sentryhub.prom")
```

### Task 2: Create the Core MetricManager Service
**Goal**: Implement the `MetricManager` singleton service in `core/services/metrics.py`.

**Steps**:
- Create `core/services/metrics.py`.
- Implement `MetricManager` as a singleton with:
  - In-memory dictionaries for counters and gauges (using `defaultdict`).
  - A `threading.Lock` for thread-safe updates.
  - Methods: `inc_counter(name, labels, value)`, `set_gauge(name, labels, value)`, and `_format_labels(labels)`.
  - A placeholder `write_metrics()` method.
- Create a global instance: `metrics_manager = MetricManager()`.

### Task 3: Implement Atomic File Writing Logic
**Goal**: Add logic to `MetricManager` for atomic file writes in `core/services/metrics.py`.

**Steps**:
- Implement `write_metrics()` to:
  - Iterate through `self.counters` and `self.gauges`.
  - Format metrics into Prometheus text format (with `# TYPE` lines).
  - Use `tempfile.mkstemp` for a temporary file.
  - Write formatted metrics and use `os.rename` for atomicity.
  - Handle errors with try-except and logging.

### Task 4: Create a Periodic Celery Task
**Goal**: Create a Celery task to periodically call `write_metrics()`.

**Files**:
- `core/tasks.py` (create if needed).
- `sentryHub/settings.py` (for Celery Beat configuration).

**Steps**:
- Define `flush_metrics_to_file` task in `core/tasks.py` to call `metrics_manager.write_metrics()`.
- Configure `CELERY_BEAT_SCHEDULE` in `sentryHub/settings.py` to run the task every 15 seconds.

**Example**:
```python
# core/tasks.py
from celery import shared_task
from .services.metrics import metrics_manager
from django.conf import settings

@shared_task
def flush_metrics_to_file():
    if settings.METRICS_ENABLED:
        metrics_manager.write_metrics()

# sentryHub/settings.py
from datetime import timedelta
CELERY_BEAT_SCHEDULE = {
    'flush-metrics-every-15-seconds': {
        'task': 'core.tasks.flush_metrics_to_file',
        'schedule': timedelta(seconds=15),
    },
}
```

### Task 5: Integrate Metrics into Jira Service
**Goal**: Add metrics for the Jira integration in `integrations/services/jira_service.py`.

**Steps**:
- Import `metrics_manager` and `settings`.
- In `JiraService.__init__`:
  - On client initialization failure (if `METRICS_ENABLED`), increment `sentryhub_component_initialization_errors_total{component="jira"}`.
- For API call methods (e.g., `create_issue`, `add_comment`):
  - Increment `sentryhub_jira_api_calls_total{status="failure", method="..."}` in except blocks.
  - On success, increment `sentryhub_jira_api_calls_total{status="success", method="..."}` and set `sentryhub_component_last_successful_api_call_timestamp{component="jira"}`.

### Task 6: Documentation and Alerting Rules
**Goal**: Document the framework and provide alerting rules in `documentations/INTERNAL_METRICS.md`.

**Steps**:
- Create a Markdown file explaining:
  - How to add metrics using `metrics_manager`.
  - Example usage from `JiraService`.
  - List of implemented metrics.
- Include Prometheus alerting rules.

**Example Alerting Rules**:
```yaml
groups:
- name: SentryHub.Internal.Jira
  rules:
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
```

## Usage
To add a new metric:
1. Import `metrics_manager` from `core.services.metrics`.
2. Call `metrics_manager.inc_counter(name, labels, value)` or `metrics_manager.set_gauge(name, labels, value)` as needed.
3. Ensure `settings.METRICS_ENABLED` is `True` for metrics to be processed.

## Notes
- Ensure the directory for `METRICS_FILE_PATH` exists and has correct permissions for `node_exporter`.
- The framework is designed to be lightweight and extensible, supporting additional metric types and components as needed.