from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from docs.models import AlertDocumentation, DocumentationAlertGroup
from alerts.models import AlertGroup
from django.utils import timezone
from datetime import timedelta


User = get_user_model()


class AlertDocumentationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.documentation = AlertDocumentation.objects.create(
            title='Test Alert',
            description='<p>This is a test description.</p>',
            created_by=self.user
        )

    def test_alert_documentation_creation(self):
        self.assertEqual(AlertDocumentation.objects.count(), 1)
        doc = AlertDocumentation.objects.get(title='Test Alert')
        self.assertEqual(doc.description, '<p>This is a test description.</p>')
        self.assertEqual(doc.created_by, self.user)
        self.assertIsNotNone(doc.created_at)
        self.assertIsNotNone(doc.updated_at)

    def test_str_representation(self):
        self.assertEqual(str(self.documentation), 'Test Alert')

    def test_ordering(self):
        AlertDocumentation.objects.create(title='Another Alert', description='<p>Desc</p>', created_by=self.user)
        AlertDocumentation.objects.create(title='Zebra Alert', description='<p>Desc</p>', created_by=self.user)
        docs = AlertDocumentation.objects.all()
        self.assertEqual(docs[0].title, 'Another Alert')
        self.assertEqual(docs[1].title, 'Test Alert')
        self.assertEqual(docs[2].title, 'Zebra Alert')


class DocumentationAlertGroupModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.documentation = AlertDocumentation.objects.create(
            title='Test Alert Doc',
            description='<p>Description</p>',
            created_by=self.user
        )
        self.alert_group = AlertGroup.objects.create(
            name='Test Alert Group',
            fingerprint='testfingerprint123',
            labels={},
            current_status='firing',
            severity='critical',
            first_occurrence=timezone.now()
        )
        self.doc_alert_group = DocumentationAlertGroup.objects.create(
            documentation=self.documentation,
            alert_group=self.alert_group,
            linked_by=self.user
        )

    def test_documentation_alert_group_creation(self):
        self.assertEqual(DocumentationAlertGroup.objects.count(), 1)
        link = DocumentationAlertGroup.objects.get(documentation=self.documentation, alert_group=self.alert_group)
        self.assertEqual(link.documentation, self.documentation)
        self.assertEqual(link.alert_group, self.alert_group)
        self.assertEqual(link.linked_by, self.user)
        self.assertIsNotNone(link.linked_at)

    def test_unique_together_constraint(self):
        with self.assertRaises(IntegrityError):
            DocumentationAlertGroup.objects.create(
                documentation=self.documentation,
                alert_group=self.alert_group,
                linked_by=self.user
            )

    def test_cascade_on_documentation_delete(self):
        self.documentation.delete()
        self.assertEqual(DocumentationAlertGroup.objects.count(), 0)

    def test_cascade_on_alert_group_delete(self):
        self.alert_group.delete()
        self.assertEqual(DocumentationAlertGroup.objects.count(), 0)