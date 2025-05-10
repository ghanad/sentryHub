import logging
import pika
import json
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from alerts.tasks import process_alert_payload_task # Ensure this is the correct path to your Celery task

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Starts a robust RabbitMQ consumer to process external alerts from a queue with retry logic.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initializing RabbitMQ consumer...'))
        logger.info("Initializing RabbitMQ consumer for external alerts.")

        rabbitmq_config = settings.RABBITMQ_CONFIG
        retry_delay = rabbitmq_config.get('RETRY_DELAY', 30)

        while True: # Outer loop for connection retries
            connection = None
            try:
                self.stdout.write(f"Attempting to connect to RabbitMQ host: {rabbitmq_config['HOST']}...")
                logger.info(f"Attempting to connect to RabbitMQ host: {rabbitmq_config['HOST']}:{rabbitmq_config['PORT']}")
                
                credentials = pika.PlainCredentials(rabbitmq_config['USER'], rabbitmq_config['PASSWORD'])
                parameters = pika.ConnectionParameters(
                    host=rabbitmq_config['HOST'],
                    port=rabbitmq_config['PORT'],
                    credentials=credentials,
                    heartbeat=rabbitmq_config.get('HEARTBEAT', 600),
                    blocked_connection_timeout=rabbitmq_config.get('BLOCKED_CONNECTION_TIMEOUT', 300)
                )
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                self.stdout.write(self.style.SUCCESS('Successfully connected to RabbitMQ.'))
                logger.info("Successfully connected to RabbitMQ.")

                queue_name = rabbitmq_config['EXTERNAL_QUEUE']
                channel.queue_declare(queue=queue_name, durable=True)
                logger.info(f"Declared queue: {queue_name}")

                # Set Quality of Service: Process one message at a time
                channel.basic_qos(prefetch_count=1)
                logger.info("QoS prefetch_count set to 1.")

                def on_message_callback(ch, method, properties, body):
                    message_tag = method.delivery_tag
                    try:
                        logger.debug(f"Received raw message (tag: {message_tag}).")
                        payload_str = body.decode('utf-8')
                        
                        # Initial JSON Validation
                        try:
                            payload = json.loads(payload_str)
                            logger.info(f"[<] Received valid JSON message (tag: {message_tag}): {payload_str[:250]}...")
                        except json.JSONDecodeError as e_json:
                            logger.error(f"[!] Failed to decode JSON (tag: {message_tag}): {payload_str[:250]}... Error: {e_json}")
                            ch.basic_nack(delivery_tag=message_tag, requeue=False)
                            logger.warning(f"[-] NACKed message (tag: {message_tag}) due to JSON decode error (no requeue).")
                            return # Stop processing this message

                        # Send to Celery task
                        # Ensure process_alert_payload_task is correctly imported and is a Celery task
                        process_alert_payload_task.delay(payload)
                        alert_name = payload.get('commonLabels', {}).get('alertname', 'N/A')
                        logger.info(f"[>] Dispatched message (tag: {message_tag}, alert: {alert_name}) to Celery.")
                        
                        ch.basic_ack(delivery_tag=message_tag)
                        logger.info(f"[v] ACKed message (tag: {message_tag}, alert: {alert_name}).")

                    except Exception as e_process:
                        # Catch any other exception during processing
                        logger.error(f"[!] Error processing message (tag: {message_tag}): {e_process}", exc_info=True)
                        try:
                            ch.basic_nack(delivery_tag=message_tag, requeue=False)
                            logger.warning(f"[-] NACKed message (tag: {message_tag}) due to processing error (no requeue).")
                        except Exception as e_nack:
                            logger.error(f"[!!] Failed to NACK message (tag: {message_tag}) after processing error: {e_nack}", exc_info=True)
                            # This is a critical state, consumer might need to be restarted or channel re-established

                channel.basic_consume(queue=queue_name, on_message_callback=on_message_callback)

                self.stdout.write(self.style.SUCCESS(f"Consumer started. Waiting for messages on queue '{queue_name}'. Press Ctrl+C to exit."))
                logger.info(f"Consumer started. Waiting for messages on queue '{queue_name}'.")
                channel.start_consuming() # This is a blocking call

            except (pika.exceptions.AMQPConnectionError, 
                    pika.exceptions.ChannelClosedByBroker, 
                    pika.exceptions.ChannelWrongStateError,
                    pika.exceptions.StreamLostError) as e_conn:
                logger.error(f"RabbitMQ connection/channel error: {e_conn}", exc_info=True)
                self.stderr.write(self.style.ERROR(f"RabbitMQ connection/channel error: {e_conn}"))
                if connection and connection.is_open:
                    try:
                        connection.close()
                        logger.info("RabbitMQ connection closed due to error.")
                    except Exception as e_close:
                        logger.error(f"Error closing RabbitMQ connection during error handling: {e_close}", exc_info=True)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\nRabbitMQ consumer stopping due to KeyboardInterrupt.'))
                logger.info("RabbitMQ consumer stopping due to KeyboardInterrupt.")
                break # Exit the while True loop
            except Exception as e_main:
                logger.error(f"An unexpected error occurred in the main consumer loop: {e_main}", exc_info=True)
                self.stderr.write(self.style.ERROR(f"An unexpected error occurred: {e_main}"))
            finally:
                if connection and connection.is_open:
                    try:
                        connection.close()
                        logger.info("RabbitMQ connection closed in finally block.")
                    except Exception as e_close_finally:
                        logger.error(f"Error closing RabbitMQ connection in finally block: {e_close_finally}", exc_info=True)
                
                if isinstance(e_conn, KeyboardInterrupt): # type: ignore
                     break # Ensure exit from while loop if KeyboardInterrupt was caught by AMQP errors

            self.stdout.write(self.style.WARNING(f"Consumer loop iteration ended. Retrying in {retry_delay} seconds..."))
            logger.info(f"Consumer loop iteration ended. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        
        self.stdout.write(self.style.SUCCESS('RabbitMQ consumer shut down completely.'))
        logger.info("RabbitMQ consumer shut down completely.")