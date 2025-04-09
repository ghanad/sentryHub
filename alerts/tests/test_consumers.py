import pytest
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TestCase
from alerts.consumers import AlertConsumer
from alerts.models import AlertInstance, AlertGroup
from asgiref.sync import sync_to_async

class TestAlertConsumer(TestCase):
    @pytest.mark.asyncio
    async def test_consumer_connect(self):
        communicator = WebsocketCommunicator(AlertConsumer.as_asgi(), "/ws/alerts/")
        connected, _ = await communicator.connect()
        assert connected

        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_consumer_disconnect(self):
        communicator = WebsocketCommunicator(AlertConsumer.as_asgi(), "/ws/alerts/")
        connected, _ = await communicator.connect()
        assert connected

        await communicator.disconnect()
        
        
    @pytest.mark.asyncio
    async def test_send_alert_update(self):
        await database_sync_to_async(AlertGroup.objects.create)(name='test', description='test')

        alert_group = await database_sync_to_async(AlertGroup.objects.get)(name='test')
        await database_sync_to_async(AlertInstance.objects.create)(alert_group=alert_group, message='test')

        communicator = WebsocketCommunicator(AlertConsumer.as_asgi(), "/ws/alerts/")
        connected, _ = await communicator.connect()
        assert connected

        alert_data = {
            "id": 1,
            "message": "Test Alert",
            "status": "firing",
            "alert_group":{
                'name':'test',
                'description':'test'
            }
        }
        await AlertConsumer.send_alert_update(alert_data)

        response = await communicator.receive_json_from()

        assert response == alert_data

        await communicator.disconnect()