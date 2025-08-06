import json
from channels.generic.websocket import AsyncWebsocketConsumer


class AlertsConsumer(AsyncWebsocketConsumer):
    group_name = "alerts_stream"

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)  # Unauthorized
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            # Safe to ignore if already discarded
            pass

    async def receive(self, text_data=None, bytes_data=None):
        # Push-only consumer; clients don't send messages
        return

    async def alert_event(self, event):
        """
        Handler for group_send events with type 'alert.event'
        Expects event = {"type": "alert.event", "payload": {...}}
        """
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps(payload))