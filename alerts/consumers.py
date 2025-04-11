import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)


class AlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info(f"connect called {self.channel_name}")
        try:
            self.room_group_name = "alerts"

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            await self.accept()
        except Exception as e:
            logger.error(f"Error in connect: {e}")

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        except Exception as e:
            logger.error(f"Error in disconnect: {e}")

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json["message"]
            
            await self.channel_layer.group_send(
                self.room_group_name, {"type": "alert_message", "message": message}
            )
        except Exception as e:
            logger.error(f"Error in receive: {e}")

    async def alert_message(self, event):
        try:
            logger.info("alert_message called")
            message = event["message"]
            await self.send(text_data=json.dumps({"message": message}))
        except Exception as e:
            logger.error(f"Error in alert_message: {e}")

    @classmethod
    def send_alert_update(cls, message):
        logger.info("send_alert_update called")
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "alerts", {"type": "alert_message", "message": message}
            )
        except Exception as e:
            logger.error(f"Error in send_alert_update: {e}")