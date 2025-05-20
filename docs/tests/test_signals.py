import logging
from unittest.mock import patch, call

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from alerts.models import AlertGroup
from docs.models import AlertDocumentation, DocumentationAlertGroup
# from docs.signals import handle_documentation_save # Signal handler is connected via apps.py

# Suppress logging output during tests unless specifically testing for it
logging.disable(logging.CRITICAL)

class HandleDocumentationSaveSignalTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='docs_signal_user1', password='password123')
        self.user2 = User.objects.create_user(username='docs_signal_user2', password='password456')

        # AlertGroups to be matched against
        self.ag_cpu_high = AlertGroup.objects.create(
            fingerprint='fp-signal-cpu',
            name='CPU High Usage', # Exact match for doc1 title
            severity='critical'
        )
        self.ag_cpu_high_lower = AlertGroup.objects.create(
            fingerprint='fp-signal-cpu-lower',
            name='cpu high usage', # Lowercase match for doc1 title (if case-insensitive)
            severity='warning'
        )
        self.ag_memory_leak = AlertGroup.objects.create(
            fingerprint='fp-signal-memory',
            name='Memory Leak Investigation', # Will match doc2 title
            severity='high'
        )
        self.ag_other = AlertGroup.objects.create(
            fingerprint='fp-signal-other',
            name='Other Unrelated Alert',
            severity='info'
        )

        # Data for creating AlertDocumentation instances
        self.doc1_data_cpu = {
            'title': 'CPU High Usage',
            'description': 'Documentation for high CPU.',
            'created_by': self.user1
        }
        self.doc2_data_memory = {
            'title': 'Memory Leak Investigation',
            'description': 'How to find memory leaks.',
            'created_by': self.user2
        }

    @patch('docs.signals.logger') # Mock the logger in docs.signals
    def test_new_doc_matches_alert_groups(self, mock_logger):
        """ New doc title matches existing AlertGroup names, links should be created. """
        # AlertGroup names are 'CPU High Usage' and 'cpu high usage'
        # Create a new doc with title 'CPU High Usage'
        new_doc = AlertDocumentation.objects.create(**self.doc1_data_cpu)
        
        # Check links (case-sensitive match by default in the signal handler's filter)
        self.assertTrue(
            DocumentationAlertGroup.objects.filter(documentation=new_doc, alert_group=self.ag_cpu_high).exists()
        )
        link1 = DocumentationAlertGroup.objects.get(documentation=new_doc, alert_group=self.ag_cpu_high)
        self.assertEqual(link1.linked_by, self.user1) # created_by of the doc

        # Check if it also linked to the lowercase name AlertGroup (depends on filter logic in signal)
        # The current signal uses AlertGroup.objects.filter(name=instance.title), which is case-sensitive
        # So, it should NOT link to self.ag_cpu_high_lower unless title was 'cpu high usage'
        self.assertFalse(
            DocumentationAlertGroup.objects.filter(documentation=new_doc, alert_group=self.ag_cpu_high_lower).exists()
        )
        
        # Create another doc with lowercase title
        doc_lower_title_data = self.doc1_data_cpu.copy()
        doc_lower_title_data['title'] = 'cpu high usage'
        new_doc_lower = AlertDocumentation.objects.create(**doc_lower_title_data)
        self.assertTrue(
            DocumentationAlertGroup.objects.filter(documentation=new_doc_lower, alert_group=self.ag_cpu_high_lower).exists()
        )
        link_lower = DocumentationAlertGroup.objects.get(documentation=new_doc_lower, alert_group=self.ag_cpu_high_lower)
        self.assertEqual(link_lower.linked_by, self.user1)

        # Verify no link to unrelated alert group
        self.assertFalse(
            DocumentationAlertGroup.objects.filter(documentation=new_doc, alert_group=self.ag_other).exists()
        )
        mock_logger.info.assert_any_call(f"Documentation '{new_doc.title}' created/updated. Attempting to link to matching AlertGroups.")


    def test_new_doc_no_matching_alert_groups(self):
        # Create a new doc with a title that doesn't match any AlertGroup names
        doc_no_match_data = {
            'title': 'Unique Non-Matching Title',
            'description': 'No alert groups should match this.',
            'created_by': self.user1
        }
        new_doc_no_match = AlertDocumentation.objects.create(**doc_no_match_data)
        
        self.assertFalse(
            DocumentationAlertGroup.objects.filter(documentation=new_doc_no_match).exists()
        )

    def test_existing_doc_update_title_unchanged(self):
        # Create doc and initial link
        doc = AlertDocumentation.objects.create(**self.doc1_data_cpu) # Links to self.ag_cpu_high
        self.assertTrue(DocumentationAlertGroup.objects.filter(documentation=doc, alert_group=self.ag_cpu_high).exists())
        initial_link_count = DocumentationAlertGroup.objects.count()

        # Update description (non-title field)
        doc.description = "Updated description, title is the same."
        doc.save() # Triggers post_save signal

        # No new links should be created, existing link should remain
        self.assertEqual(DocumentationAlertGroup.objects.count(), initial_link_count)
        self.assertTrue(DocumentationAlertGroup.objects.filter(documentation=doc, alert_group=self.ag_cpu_high).exists())

    def test_existing_doc_update_title_changed_matches_new_alerts(self):
        # Initial state: doc1 ("CPU High Usage") linked to ag_cpu_high ("CPU High Usage")
        doc1 = AlertDocumentation.objects.create(**self.doc1_data_cpu)
        self.assertTrue(DocumentationAlertGroup.objects.filter(documentation=doc1, alert_group=self.ag_cpu_high).exists())
        
        # ag_memory_leak ("Memory Leak Investigation") is not linked to doc1 initially
        self.assertFalse(DocumentationAlertGroup.objects.filter(documentation=doc1, alert_group=self.ag_memory_leak).exists())

        # Update doc1's title to match ag_memory_leak's name
        doc1.title = self.ag_memory_leak.name # "Memory Leak Investigation"
        doc1.save() # Triggers post_save

        # New link should be created for ag_memory_leak
        self.assertTrue(
            DocumentationAlertGroup.objects.filter(documentation=doc1, alert_group=self.ag_memory_leak).exists()
        )
        new_link = DocumentationAlertGroup.objects.get(documentation=doc1, alert_group=self.ag_memory_leak)
        self.assertEqual(new_link.linked_by, self.user1) # doc1.created_by

        # As per signal's current logic, the old link to ag_cpu_high is NOT removed.
        self.assertTrue(DocumentationAlertGroup.objects.filter(documentation=doc1, alert_group=self.ag_cpu_high).exists())

    @patch('docs.signals.logger')
    @patch('docs.models.DocumentationAlertGroup.objects.get_or_create')
    def test_exception_during_get_or_create(self, mock_get_or_create, mock_logger):
        mock_get_or_create.side_effect = IntegrityError("Simulated DB error during get_or_create")
        
        # This creation will trigger the signal, which will then call the mocked get_or_create
        with self.assertLogs(logger='docs.signals', level='ERROR') as cm:
             AlertDocumentation.objects.create(**self.doc1_data_cpu)
        
        # Verify logging
        mock_logger.error.assert_called_once()
        self.assertIn(f"Error linking documentation '{self.doc1_data_cpu['title']}' to alert group '{self.ag_cpu_high.name}'", mock_logger.error.call_args[0][0])
        self.assertTrue(isinstance(mock_logger.error.call_args[0][1], IntegrityError))

        # Ensure no link was actually created if get_or_create failed catastrophically
        # (though get_or_create itself might create before erroring in some scenarios, here we assume it doesn't complete)
        self.assertFalse(DocumentationAlertGroup.objects.filter(documentation__title=self.doc1_data_cpu['title']).exists())
