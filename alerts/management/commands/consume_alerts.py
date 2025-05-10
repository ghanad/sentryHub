import logging
import pika
import json
import time # Keep for potential reconnection logic
from django.core.management.base import BaseCommand
from django.conf import settings
from alerts.tasks import process_alert_payload_task # Make sure this path is correct

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Starts a RabbitMQ consumer to process alerts from a queue.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Attempting to start RabbitMQ consumer...'))
        logger.info("Attempting to start RabbitMQ consumer.")

        connection = None
        try:
            credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=600,  # Keep connection alive
                blocked_connection_timeout=300 # Timeout for blocked connections
            )
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            channel.queue_declare(queue=settings.RABBITMQ_QUEUE, durable=True)
            logger.info(f"Declared queue: {settings.RABBITMQ_QUEUE}")

            def callback(ch, method, properties, body):
                try:
                    payload_str = body.decode('utf-8')
                    logger.info(f"Received message: {payload_str[:200]}...") # Log snippet
                    payload = json.loads(payload_str)
                    
                    # Send to Celery task
                    process_alert_payload_task.delay(payload)
                    logger.info(f"Sent payload to Celery task for alert: {payload.get('commonLabels', {}).get('alertname', 'N/A')}")
                    
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.debug(f"Acknowledged message: {method.delivery_tag}")
                except json.JSONDecodeError as e_json:
                    logger.error(f"Failed to decode JSON from message: {body.decode('utf-8', errors='ignore')[:200]}... Error: {e_json}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # Do not requeue malformed JSON
                except Exception as e_process:
                    logger.error(f"Error processing message: {e_process}", exc_info=True)
                    # Requeue on other processing errors, so it can be retried
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            channel.basic_qos(prefetch_count=1) # Process one message at a time
            channel.basic_consume(queue=settings.RABBITMQ_QUEUE, on_message_callback=callback)

            self.stdout.write(self.style.SUCCESS(f"Consumer started. Waiting for messages on queue '{settings.RABBITMQ_QUEUE}'. Press Ctrl+C to exit."))
            logger.info(f"Consumer started. Waiting for messages on queue '{settings.RABBITMQ_QUEUE}'.")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e_conn:
            logger.error(f"RabbitMQ connection error: {e_conn}", exc_info=True)
            self.stderr.write(self.style.ERROR(f"RabbitMQ connection error: {e_conn}. Check settings and RabbitMQ server."))
            # Optional: Add more sophisticated reconnection logic here if needed
            self.stdout.write(self.style.WARNING("Will attempt to reconnect in 10 seconds..."))
            time.sleep(10) # Wait before exiting or attempting to reconnect
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nRabbitMQ consumer stopped by user.'))
            logger.info("RabbitMQ consumer stopped by user.")
        except Exception as e_main:
            logger.error(f"An unexpected error occurred in the RabbitMQ consumer: {e_main}", exc_info=True)
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred: {e_main}"))
        finally:
            if connection and connection.is_open:
                try:
                    connection.close()
                    logger.info("RabbitMQ connection closed.")
                except Exception as e_close:
                    logger.error(f"Error closing RabbitMQ connection: {e_close}", exc_info=True)
            self.stdout.write(self.style.SUCCESS('RabbitMQ consumer shut down.'))
            logger.info("RabbitMQ consumer shut down.")