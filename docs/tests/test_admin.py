from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from docs.models import AlertDocumentation, DocumentationAlertGroup
from alerts.models import AlertGroup
from docs.admin import AlertDocumentationAdmin, DocumentationAlertGroupAdmin, DocumentationAlertGroupInline
from unittest.mock import Mock

User = get_user_model()

class MockRequest:
    def __init__(self, user):
        self.user = user

class AlertDocumentationAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = AlertDocumentationAdmin(AlertDocumentation, self.site)
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpassword', email='admin@example.com')

    def test_save_model_new_object(self):
        # Test that created_by is set for a new object
        mock_request = MockRequest(user=self.user)
        form = Mock()
        obj = AlertDocumentation(title='New Doc', description='<p>New Description</p>')
        
        self.assertIsNone(obj.created_by)
        self.admin.save_model(mock_request, obj, form, False) # False indicates new object
        self.assertEqual(obj.created_by, self.user)

    def test_save_model_existing_object(self):
        # Test that created_by is not changed for an existing object
        existing_doc = AlertDocumentation.objects.create(
            title='Existing Doc', description='<p>Existing Description</p>', created_by=self.user
        )
        mock_request = MockRequest(user=self.admin_user)
        form = Mock()
        
        self.assertEqual(existing_doc.created_by, self.user)
        self.admin.save_model(mock_request, existing_doc, form, True) # True indicates existing object
        existing_doc.refresh_from_db()
        self.assertEqual(existing_doc.created_by, self.user) # Should remain the original user


class DocumentationAlertGroupAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = DocumentationAlertGroupAdmin(DocumentationAlertGroup, self.site)
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.documentation = AlertDocumentation.objects.create(
            title='Test Doc', description='<p>Test Description</p>', created_by=self.user
        )
        self.alert_group = AlertGroup.objects.create(
            fingerprint='test_fp', name='Test Alert Group', labels={'job': 'test'}, severity='critical', current_status='firing'
        )
        self.doc_alert_group = DocumentationAlertGroup.objects.create(
            documentation=self.documentation, alert_group=self.alert_group, linked_by=self.user
        )

    def test_list_display(self):
        # Check if list_display fields are correctly defined
        self.assertEqual(self.admin.list_display, ('documentation', 'alert_group', 'linked_at', 'linked_by'))

    def test_list_filter(self):
        # Check if list_filter fields are correctly defined
        self.assertEqual(self.admin.list_filter, ('linked_at',))

    def test_search_fields(self):
        # Check if search_fields are correctly defined
        self.assertEqual(self.admin.search_fields, ('documentation__title', 'alert_group__name'))

    def test_readonly_fields(self):
        # Check if readonly_fields are correctly defined
        self.assertEqual(self.admin.readonly_fields, ('linked_at',))

    def test_date_hierarchy(self):
        # Check if date_hierarchy is correctly defined
        self.assertEqual(self.admin.date_hierarchy, 'linked_at')


class DocumentationAlertGroupInlineTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.inline = DocumentationAlertGroupInline(AlertDocumentation, self.site)

    def test_model(self):
        self.assertEqual(self.inline.model, DocumentationAlertGroup)

    def test_extra(self):
        self.assertEqual(self.inline.extra, 0)

    def test_readonly_fields(self):
        self.assertEqual(self.inline.readonly_fields, ('alert_group', 'linked_at', 'linked_by'))

    def test_can_delete(self):
        self.assertFalse(self.inline.can_delete)