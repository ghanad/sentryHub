from django.test import TestCase
from django.contrib.auth import get_user_model
from docs.models import AlertDocumentation, DocumentationAlertGroup
from alerts.models import AlertGroup
from docs.api.serializers import AlertDocumentationSerializer, DocumentationAlertGroupSerializer
from django.utils import timezone

User = get_user_model()

class AlertDocumentationSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword', first_name='Test', last_name='User')
        self.documentation = AlertDocumentation.objects.create(
            title='Test Doc',
            description='<p>Test Description</p>',
            created_by=self.user
        )
        self.serializer = AlertDocumentationSerializer(instance=self.documentation)

    def test_serializer_fields(self):
        data = self.serializer.data
        self.assertEqual(set(data.keys()), set(['id', 'title', 'description', 'created_at', 'updated_at', 'created_by', 'created_by_name']))

    def test_created_by_name_method(self):
        data = self.serializer.data
        self.assertEqual(data['created_by_name'], 'Test User')

    def test_created_by_name_no_full_name(self):
        self.user.first_name = ''
        self.user.last_name = ''
        self.user.save()
        self.documentation.refresh_from_db()
        serializer = AlertDocumentationSerializer(instance=self.documentation)
        data = serializer.data
        self.assertEqual(data['created_by_name'], 'testuser')

    def test_created_by_name_no_user(self):
        self.documentation.created_by = None
        self.documentation.save()
        serializer = AlertDocumentationSerializer(instance=self.documentation)
        data = serializer.data
        self.assertIsNone(data['created_by_name'])

    def test_serialization_data(self):
        data = self.serializer.data
        self.assertEqual(data['id'], self.documentation.id)
        self.assertEqual(data['title'], self.documentation.title)
        self.assertEqual(data['description'], self.documentation.description)
        self.assertEqual(data['created_by'], self.user.id)
        # Check datetime format (it will be ISO 8601 string)
        self.assertIn('T', data['created_at'])
        self.assertRegex(data['created_at'], r'[+-]\d{2}:\d{2}$') # Check for timezone offset
        self.assertIn('T', data['updated_at'])
        self.assertRegex(data['updated_at'], r'[+-]\d{2}:\d{2}$') # Check for timezone offset


class DocumentationAlertGroupSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword', first_name='Test', last_name='User')
        self.documentation = AlertDocumentation.objects.create(
            title='Test Doc',
            description='<p>Test Description</p>',
            created_by=self.user
        )
        self.alert_group = AlertGroup.objects.create(
            fingerprint='test_fp', name='Test Alert Group', labels={'job': 'test'}, severity='critical', current_status='firing'
        )
        self.doc_alert_group = DocumentationAlertGroup.objects.create(
            documentation=self.documentation, alert_group=self.alert_group, linked_by=self.user
        )
        self.serializer = DocumentationAlertGroupSerializer(instance=self.doc_alert_group)

    def test_serializer_fields(self):
        data = self.serializer.data
        expected_fields = set([
            'id', 'documentation', 'alert_group', 'linked_at', 'linked_by',
            'documentation_details', 'alert_group_details', 'linked_by_name'
        ])
        self.assertEqual(set(data.keys()), expected_fields)

    def test_documentation_details_method(self):
        data = self.serializer.data
        self.assertEqual(data['documentation_details']['id'], self.documentation.id)
        self.assertEqual(data['documentation_details']['title'], self.documentation.title)

    def test_alert_group_details_method(self):
        data = self.serializer.data
        self.assertEqual(data['alert_group_details']['id'], self.alert_group.id)
        self.assertEqual(data['alert_group_details']['name'], self.alert_group.name)
        self.assertEqual(data['alert_group_details']['fingerprint'], self.alert_group.fingerprint)
        self.assertEqual(data['alert_group_details']['current_status'], self.alert_group.current_status)

    def test_linked_by_name_method(self):
        data = self.serializer.data
        self.assertEqual(data['linked_by_name'], 'Test User')

    def test_linked_by_name_no_full_name(self):
        self.user.first_name = ''
        self.user.last_name = ''
        self.user.save()
        self.doc_alert_group.refresh_from_db()
        serializer = DocumentationAlertGroupSerializer(instance=self.doc_alert_group)
        data = serializer.data
        self.assertEqual(data['linked_by_name'], 'testuser')

    def test_linked_by_name_no_user(self):
        self.doc_alert_group.linked_by = None
        self.doc_alert_group.save()
        serializer = DocumentationAlertGroupSerializer(instance=self.doc_alert_group)
        data = serializer.data
        self.assertIsNone(data['linked_by_name'])

    def test_serialization_data(self):
        data = self.serializer.data
        self.assertEqual(data['id'], self.doc_alert_group.id)
        self.assertEqual(data['documentation'], self.documentation.id)
        self.assertEqual(data['alert_group'], self.alert_group.id)
        self.assertEqual(data['linked_by'], self.user.id)
        self.assertIn('T', data['linked_at'])
        self.assertRegex(data['linked_at'], r'[+-]\d{2}:\d{2}$') # Check for timezone offset