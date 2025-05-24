from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from alerts.models import AlertGroup
from docs.models import AlertDocumentation, DocumentationAlertGroup
from docs.services.documentation_matcher import match_documentation_to_alert, get_documentation_for_alert
from users.models import UserProfile
from django.contrib.auth import get_user_model
from docs.signals import handle_documentation_save
from django.db.models.signals import post_save # Import post_save

User = get_user_model()

class DocumentationMatcherServiceTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Disconnect the signal during tests to prevent automatic link creation
        post_save.disconnect(handle_documentation_save, sender=AlertDocumentation)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Reconnect the signal after tests
        post_save.connect(handle_documentation_save, sender=AlertDocumentation)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password', email='test@example.com')
        self.user_profile = UserProfile.objects.get(user=self.user) # UserProfile is created automatically by a signal
        self.alert_group_name = "Test Alert Group"
        self.alert_group = AlertGroup.objects.create(name=self.alert_group_name, fingerprint="testfingerprint123", labels={})
        self.documentation = AlertDocumentation.objects.create(title=self.alert_group_name, description="Test Description")
        self.other_documentation = AlertDocumentation.objects.create(title="Other Doc", description="Other Description")

    def test_match_documentation_to_alert_exact_match_new_link(self):
        """
        Test that documentation is matched and a new link is created when an exact title match exists.
        """
        matched_doc = match_documentation_to_alert(self.alert_group)
        self.assertIsNotNone(matched_doc)
        self.assertEqual(matched_doc, self.documentation)
        self.assertTrue(DocumentationAlertGroup.objects.filter(
            documentation=self.documentation,
            alert_group=self.alert_group
        ).exists())

    def test_match_documentation_to_alert_exact_match_existing_link(self):
        """
        Test that documentation is matched and no new link is created if a link already exists.
        """
        DocumentationAlertGroup.objects.create(
            documentation=self.documentation,
            alert_group=self.alert_group,
            linked_at=timezone.now()
        )
        
        with self.assertNumQueries(2): # SELECT documentation, SELECT/INSERT DocumentationAlertGroup
            matched_doc = match_documentation_to_alert(self.alert_group)
        
        self.assertIsNotNone(matched_doc)
        self.assertEqual(matched_doc, self.documentation)
        self.assertEqual(DocumentationAlertGroup.objects.filter(
            documentation=self.documentation,
            alert_group=self.alert_group
        ).count(), 1)

    def test_match_documentation_to_alert_no_match(self):
        """
        Test that no documentation is matched when no exact title match exists.
        """
        alert_group_no_match = AlertGroup.objects.create(name="No Match Alert", fingerprint="nomatchfingerprint", labels={})
        matched_doc = match_documentation_to_alert(alert_group_no_match)
        self.assertIsNone(matched_doc)
        self.assertFalse(DocumentationAlertGroup.objects.filter(alert_group=alert_group_no_match).exists())

    def test_match_documentation_to_alert_with_user(self):
        """
        Test that the linked_by field is set correctly when a user is provided.
        """
        matched_doc = match_documentation_to_alert(self.alert_group, user=self.user)
        self.assertIsNotNone(matched_doc)
        link = DocumentationAlertGroup.objects.get(
            documentation=self.documentation,
            alert_group=self.alert_group
        )
        self.assertEqual(link.linked_by, self.user)

    @patch('docs.services.documentation_matcher.AlertDocumentation.objects.filter')
    def test_match_documentation_to_alert_exception_handling(self, mock_filter):
        """
        Test that the function handles exceptions gracefully and returns None.
        """
        mock_filter.side_effect = Exception("Database error")
        matched_doc = match_documentation_to_alert(self.alert_group)
        self.assertIsNone(matched_doc)

    def test_get_documentation_for_alert_multiple_linked(self):
        """
        Test retrieving multiple linked documentation for an alert group.
        """
        DocumentationAlertGroup.objects.create(
            documentation=self.documentation,
            alert_group=self.alert_group,
            linked_at=timezone.now()
        )
        DocumentationAlertGroup.objects.create(
            documentation=self.other_documentation,
            alert_group=self.alert_group,
            linked_at=timezone.now()
        )
        
        linked_docs = get_documentation_for_alert(self.alert_group)
        self.assertEqual(linked_docs.count(), 2)
        self.assertIn(self.documentation, linked_docs)
        self.assertIn(self.other_documentation, linked_docs)

    def test_get_documentation_for_alert_no_linked(self):
        """
        Test retrieving no linked documentation for an alert group.
        """
        alert_group_no_links = AlertGroup.objects.create(name="No Links Alert", fingerprint="nolinksfingerprint", labels={})
        linked_docs = get_documentation_for_alert(alert_group_no_links)
        self.assertEqual(linked_docs.count(), 0)

    def test_get_documentation_for_alert_one_linked(self):
        """
        Test retrieving a single linked documentation for an alert group.
        """
        DocumentationAlertGroup.objects.create(
            documentation=self.documentation,
            alert_group=self.alert_group,
            linked_at=timezone.now()
        )
        
        linked_docs = get_documentation_for_alert(self.alert_group)
        self.assertEqual(linked_docs.count(), 1)
        self.assertIn(self.documentation, linked_docs)