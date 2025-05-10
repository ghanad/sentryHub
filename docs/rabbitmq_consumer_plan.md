# RabbitMQ Consumer Integration Plan (Enhanced)

This document outlines the plan to integrate a robust RabbitMQ consumer into the SentryHub project to consume alerts from an external RabbitMQ queue.

## Objective

Add functionality to SentryHub to read alert messages from a specified RabbitMQ queue (`sentryhub_alerts_external`) and process them using the existing Celery task (`alerts.tasks.process_alert_payload_task`), in addition to the current webhook functionality. The consumer will be implemented as a resilient Django management command.

## Proposed Plan

1.  **Add RabbitMQ Configuration to `settings.py`**:
    *   Store RabbitMQ connection parameters in [`sentryHub/settings.py`](sentryHub/settings.py), preferably grouped under a dictionary like `RABBITMQ_CONFIG`.
    *   Use environment variables for sensitive details.
    *   Example structure:
        ```python
        # RabbitMQ Configuration for External Alerts
        RABBITMQ_CONFIG = {
            'HOST': os.environ.get('RABBITMQ_HOST', 'localhost'),
            'PORT': int(os.environ.get('RABBITMQ_PORT', 5672)),
            'EXTERNAL_QUEUE': os.environ.get('RABBITMQ_EXTERNAL_QUEUE', 'sentryhub_alerts_external'),
            'USER': os.environ.get('RABBITMQ_USER', 'guest'),
            'PASSWORD': os.environ.get('RABBITMQ_PASSWORD', 'guest'),
            'HEARTBEAT': int(os.environ.get('RABBITMQ_HEARTBEAT', 600)),
            'BLOCKED_CONNECTION_TIMEOUT': int(os.environ.get('RABBITMQ_BLOCKED_CONNECTION_TIMEOUT', 300)),
            'RETRY_DELAY': int(os.environ.get('RABBITMQ_RETRY_DELAY', 30)), # Seconds
        }
        ```

2.  **Install RabbitMQ Client Library**:
    *   Ensure `pika` is in your `requirements.txt` file.
    *   Run `pip install -r requirements.txt` if not already installed or updated.

3.  **Create a Django Management Command**:
    *   The command will be named `consume_rabbitmq_alerts`.
    *   Create the directory structure `alerts/management/commands/` if it doesn't exist.
    *   Create a Python file named `consume_rabbitmq_alerts.py` inside this directory.
    *   Define a custom management command class inheriting from `django.core.management.base.BaseCommand`.

4.  **Implement RabbitMQ Consumer Logic in `consume_rabbitmq_alerts.py`**:
    *   **Main `handle` Method:**
        *   Implement an outer `while True` loop to manage connection retries.
        *   Inside the loop, attempt to establish a connection to RabbitMQ.
        *   Use `pika.ConnectionParameters` with `host`, `port`, `credentials`, `heartbeat`, and `blocked_connection_timeout` from `settings.RABBITMQ_CONFIG`.
        *   Handle `pika.exceptions.AMQPConnectionError`, `pika.exceptions.ChannelClosedByBroker`, `pika.exceptions.ChannelWrongStateError`, and other relevant Pika exceptions.
        *   On connection failure, log the error and the retry attempt, then `time.sleep(settings.RABBITMQ_CONFIG.get('RETRY_DELAY', 30))` before the next iteration of the outer loop.
    *   **Channel and Queue Setup (within successful connection block):**
        *   Create a channel.
        *   Declare the queue (e.g., `settings.RABBITMQ_CONFIG['EXTERNAL_QUEUE']`) with `durable=True`.
        *   Set Quality of Service: `channel.basic_qos(prefetch_count=1)`.
    *   **Callback Function (`on_message_callback`):**
        *   **Initial JSON Validation:** Try to decode the message `body` using `json.loads()`. If `json.JSONDecodeError` occurs, log the error and NACK the message: `ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)`.
        *   **Message Processing:**
            *   Log the received message (e.g., a snippet or key identifiers).
            *   Dispatch the parsed payload to the Celery task: `alerts.tasks.process_alert_payload_task.delay(payload)`.
            *   Log successful dispatch to Celery (e.g., `[>] Dispatched message X to Celery.`).
        *   **Message Acknowledgement:** On successful processing and dispatch, ACK the message: `ch.basic_ack(delivery_tag=method.delivery_tag)`. Log the ACK (e.g., `[v] ACKed message X.`).
        *   **Error Handling within Callback:** Wrap the processing logic in a `try...except Exception`. If any error occurs (after JSON validation), log the specific error and NACK the message: `ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)` to prevent problematic messages from being re-queued indefinitely.
    *   **Start Consuming:**
        *   Register the callback using `channel.basic_consume()`.
        *   Start the blocking consumer loop: `channel.start_consuming()`.
    *   **Graceful Shutdown:**
        *   Handle `KeyboardInterrupt` to stop the consumer gracefully, ensuring the RabbitMQ connection is closed if open.
        *   The `finally` block in the connection `try` should close the connection.

5.  **Update Documentation**:
    *   Update project documentation to reflect:
        *   The new `RABBITMQ_CONFIG` structure in `settings.py`.
        *   Instructions for running the new management command: `python manage.py consume_rabbitmq_alerts`.
        *   Notes on its resilience and retry mechanisms.

## Architecture Diagram

```mermaid
graph LR
    A[RabbitMQ Queue (sentryhub_alerts_external)] --> B[Django Management Command (consume_rabbitmq_alerts)]
    B --> C[Celery Task Queue (Redis)]
    C --> D[Alert Processing Task]
    D --> E[SentryHub Database]
    F[Webhook] --> G[Alert Webhook View]
    G --> C
```

## Next Steps

Implement the changes in `settings.py` and create/update the `consume_rabbitmq_alerts.py` management command.