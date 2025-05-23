from django.test import TestCase, RequestFactory
from django.contrib.messages import get_messages, constants as messages_constants
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from core.context_processors import notifications

class NotificationsContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def get_request_with_messages(self):
        request = self.factory.get('/')
        # Add session and message middleware to the request
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        MessageMiddleware(lambda req: None).process_request(request)
        return request

    def test_notifications_context_processor_no_messages(self):
        """
        Test that the context processor returns an empty list when no messages are present.
        """
        request = self.get_request_with_messages()
        context = notifications(request)
        self.assertIn('django_messages', context)
        self.assertEqual(context['django_messages'], [])

    def test_notifications_context_processor_with_messages(self):
        """
        Test that the context processor correctly extracts and formats messages.
        """
        request = self.get_request_with_messages()
        
        # Add some messages
        messages_storage = get_messages(request)
        messages_storage.add(messages_constants.INFO, 'This is an info message.')
        messages_storage.add(messages_constants.WARNING, 'This is a warning message.', extra_tags='important')
        messages_storage.add(messages_constants.ERROR, 'This is an error message.')

        context = notifications(request)
        self.assertIn('django_messages', context)
        self.assertEqual(len(context['django_messages']), 3)

        # Check the first message
        self.assertEqual(context['django_messages'][0]['level'], 'info')
        self.assertEqual(context['django_messages'][0]['message'], 'This is an info message.')
        self.assertEqual(context['django_messages'][0]['extra_tags'], '')

        # Check the second message
        self.assertEqual(context['django_messages'][1]['level'], 'warning')
        self.assertEqual(context['django_messages'][1]['message'], 'This is a warning message.')
        self.assertEqual(context['django_messages'][1]['extra_tags'], 'important')

        # Check the third message
        self.assertEqual(context['django_messages'][2]['level'], 'error')
        self.assertEqual(context['django_messages'][2]['message'], 'This is an error message.')
        self.assertEqual(context['django_messages'][2]['extra_tags'], '')

    def test_notifications_context_processor_messages_present(self):
        """
        Test that messages are present in the context after being added.
        We rely on Django's framework to consume them after the response is rendered.
        """
        request = self.get_request_with_messages()
        messages_storage = get_messages(request)
        messages_storage.add(messages_constants.INFO, 'Test message.')

        # Call the context processor
        context = notifications(request)
        self.assertEqual(len(context['django_messages']), 1)
        self.assertEqual(context['django_messages'][0]['message'], 'Test message.')