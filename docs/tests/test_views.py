from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from docs.models import AlertDocumentation, DocumentationAlertGroup
from alerts.models import AlertGroup
from docs.forms import DocumentationSearchForm
import datetime
from django.utils import timezone

User = get_user_model()

class DocumentationListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpassword', email='admin@example.com')
        
        self.doc1 = AlertDocumentation.objects.create(
            title='Test Doc 1', 
            description='Description for test doc 1', 
            created_by=self.user
        )
        self.doc2 = AlertDocumentation.objects.create(
            title='Another Doc', 
            description='Another description', 
            created_by=self.user
        )
        self.doc3 = AlertDocumentation.objects.create(
            title='Third Doc', 
            description='Relevant description', 
            created_by=self.user
        )

    def test_documentation_list_view_get(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('docs:documentation-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/documentation_list.html')
        self.assertIn('documentations', response.context)
        self.assertEqual(len(response.context['documentations']), 3)
        self.assertIsInstance(response.context['search_form'], DocumentationSearchForm)
        self.assertEqual(response.context['search_query'], '')


class DocumentationDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.documentation = AlertDocumentation.objects.create(
            title='Doc', description='Desc', created_by=self.user
        )
        self.alert_newer = AlertGroup.objects.create(
            fingerprint='fp_new', name='New Alert', labels={},
            severity='critical', current_status='firing'
        )
        self.alert_older = AlertGroup.objects.create(
            fingerprint='fp_old', name='Old Alert', labels={},
            severity='critical', current_status='firing'
        )
        # Manually set last_occurrence to control ordering (use update to bypass auto_now)
        AlertGroup.objects.filter(pk=self.alert_newer.pk).update(last_occurrence=timezone.now())
        AlertGroup.objects.filter(pk=self.alert_older.pk).update(
            last_occurrence=timezone.now() - datetime.timedelta(days=1)
        )
        self.alert_newer.refresh_from_db()
        self.alert_older.refresh_from_db()
        DocumentationAlertGroup.objects.create(
            documentation=self.documentation, alert_group=self.alert_newer
        )
        DocumentationAlertGroup.objects.create(
            documentation=self.documentation, alert_group=self.alert_older
        )

    def test_linked_alerts_ordered_by_last_occurrence(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(
            reverse('docs:documentation-detail', args=[self.documentation.pk])
        )
        self.assertEqual(response.status_code, 200)
        linked_alerts = list(response.context['linked_alerts'])
        self.assertEqual(linked_alerts, [self.alert_newer, self.alert_older])

class DocumentationCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpassword', email='admin@example.com')

    def test_documentation_create_view_get_authenticated(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('docs:documentation-create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/documentation_form.html')
        self.assertIn('form', response.context)

    def test_documentation_create_view_get_unauthenticated(self):
        response = self.client.get(reverse('docs:documentation-create'))
        self.assertEqual(response.status_code, 302) # Redirect to login
        self.assertRedirects(response, f'/accounts/login/?next=/docs/new/')

    def test_documentation_create_view_post_valid_data(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('docs:documentation-create'), {
            'title': 'New Test Doc',
            'description': 'Description for new test doc',
        })
        self.assertEqual(response.status_code, 302) # Redirect on success
        new_doc = AlertDocumentation.objects.get(title='New Test Doc')
        self.assertRedirects(response, reverse('docs:documentation-detail', args=[new_doc.pk]))
        self.assertTrue(AlertDocumentation.objects.filter(title='New Test Doc').exists())
        self.assertEqual(AlertDocumentation.objects.get(title='New Test Doc').created_by, self.user)

    def test_documentation_create_view_post_invalid_data(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('docs:documentation-create'), {
            'title': '', # Invalid: title is required
            'description': 'Description for invalid doc',
        })
        self.assertEqual(response.status_code, 200) # Should render form with errors
        self.assertTemplateUsed(response, 'docs/documentation_form.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('title', response.context['form'].errors)
        self.assertFalse(AlertDocumentation.objects.filter(description='Description for invalid doc').exists())


class DocumentationUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpassword', email='admin@example.com')
        
        self.documentation = AlertDocumentation.objects.create(
            title='Original Title',
            description='<p>Original Description</p>',
            created_by=self.user
        )
        self.update_url = reverse('docs:documentation-update', kwargs={'pk': self.documentation.pk})

    def test_documentation_update_view_get_authenticated(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/documentation_form.html')
        self.assertIn('form', response.context)
        self.assertEqual(response.context['form'].instance, self.documentation)
        self.assertEqual(response.context['form'].initial['title'], 'Original Title')
        self.assertEqual(response.context['form'].initial['description'], '<p>Original Description</p>')

    def test_documentation_update_view_post_valid_data(self):
        self.client.login(username='testuser', password='testpassword')
        updated_title = 'Updated Title'
        updated_description = '<p>Updated Description Content</p>'
        response = self.client.post(self.update_url, {
            'title': updated_title,
            'description': updated_description,
        })
        self.assertEqual(response.status_code, 302) # Should redirect on success
        self.documentation.refresh_from_db()
        self.assertEqual(self.documentation.title, updated_title)
        self.assertEqual(self.documentation.description, updated_description)
        self.assertRedirects(response, reverse('docs:documentation-detail', args=[self.documentation.pk]))

        # Check for success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Documentation updated successfully.')

    def test_documentation_update_view_post_invalid_data(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(self.update_url, {
            'title': '', # Invalid: title is required
            'description': '<p>Description with invalid title</p>',
        })
        self.assertEqual(response.status_code, 200) # Should render form with errors
        self.assertTemplateUsed(response, 'docs/documentation_form.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('title', response.context['form'].errors)
        # Ensure the original documentation object was not modified
        self.documentation.refresh_from_db()
        self.assertEqual(self.documentation.title, 'Original Title')
        self.assertEqual(self.documentation.description, '<p>Original Description</p>')


class DocumentationDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpassword', email='admin@example.com')
        
        self.documentation = AlertDocumentation.objects.create(
            title='Doc to Delete',
            description='<p>Description of doc to delete</p>',
            created_by=self.user
        )
        self.delete_url = reverse('docs:documentation-delete', kwargs={'pk': self.documentation.pk})

    def test_documentation_delete_view_get_authenticated(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/documentation_confirm_delete.html')
        self.assertIn('object', response.context)
        self.assertEqual(response.context['object'], self.documentation)

    def test_documentation_delete_view_post_authenticated(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 302) # Should redirect on successful deletion
        self.assertFalse(AlertDocumentation.objects.filter(pk=self.documentation.pk).exists())
        self.assertRedirects(response, reverse('docs:documentation-list'))

        # Check for success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Documentation deleted successfully.')


class LinkDocumentationToAlertViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpassword', email='admin@example.com')
        
        self.alert_group = AlertGroup.objects.create(
            fingerprint='test_fp_link',
            name='Test Alert Group for Linking',
            labels={'job': 'test'},
            severity='critical',
            current_status='firing'
        )
        self.doc1 = AlertDocumentation.objects.create(
            title='Doc A', description='<p>Desc A</p>', created_by=self.user
        )
        self.doc2 = AlertDocumentation.objects.create(
            title='Doc B', description='<p>Desc B</p>', created_by=self.user
        )
        self.link_url = reverse('docs:link-documentation', kwargs={'pk': self.alert_group.pk})

    def test_link_documentation_to_alert_view_get_authenticated(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.link_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/link_documentation.html')
        self.assertIn('documentations', response.context)
        self.assertIn('current_docs', response.context)
        self.assertEqual(len(response.context['documentations']), 2)
        self.assertEqual(len(response.context['current_docs']), 0) # Initially no docs linked
        self.assertEqual(list(response.context['documentations']), [self.doc1, self.doc2]) # Check ordering

    def test_link_documentation_to_alert_view_post_valid_data(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(self.link_url, {'documentation_id': self.doc1.pk})
        self.assertEqual(response.status_code, 302) # Redirect on success
        self.assertTrue(DocumentationAlertGroup.objects.filter(
            documentation=self.doc1, alert_group=self.alert_group, linked_by=self.user
        ).exists())
        self.assertRedirects(response, reverse('alerts:alert-detail', args=[self.alert_group.fingerprint]))

        # Check for success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f'Alert linked to "{self.doc1.title}" documentation.')

    def test_link_documentation_to_alert_view_post_already_linked(self):
        # Link it first
        DocumentationAlertGroup.objects.create(
            documentation=self.doc1, alert_group=self.alert_group, linked_by=self.user
        )
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(self.link_url, {'documentation_id': self.doc1.pk})
        self.assertEqual(response.status_code, 302) # Redirect on success
        self.assertEqual(DocumentationAlertGroup.objects.filter(alert_group=self.alert_group).count(), 1) # Still only one link

        # Check for info message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f'Alert was already linked to this documentation.')

    def test_link_documentation_to_alert_view_post_invalid_documentation_id(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(self.link_url, {'documentation_id': 999}) # Non-existent ID
        self.assertEqual(response.status_code, 404) # Should return 404 for non-existent doc
        self.assertFalse(DocumentationAlertGroup.objects.filter(alert_group=self.alert_group).exists())


class UnlinkDocumentationFromAlertViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpassword', email='admin@example.com')
        
        self.alert_group = AlertGroup.objects.create(
            fingerprint='test_fp_unlink',
            name='Test Alert Group for Unlinking',
            labels={'job': 'test'},
            severity='critical',
            current_status='firing'
        )
        self.documentation = AlertDocumentation.objects.create(
            title='Doc to Unlink', description='<p>Desc to unlink</p>', created_by=self.user
        )
        self.doc_alert_group_link = DocumentationAlertGroup.objects.create(
            documentation=self.documentation, alert_group=self.alert_group, linked_by=self.user
        )
        self.unlink_url = reverse(
            'docs:unlink-documentation',
            kwargs={
                'alert_group_id': self.alert_group.pk,
                'documentation_id': self.documentation.pk
            }
        )

    def test_unlink_documentation_from_alert_view_post_authenticated(self):
        self.client.login(username='testuser', password='testpassword')
        self.assertTrue(DocumentationAlertGroup.objects.filter(pk=self.doc_alert_group_link.pk).exists())
        response = self.client.post(self.unlink_url)
        self.assertEqual(response.status_code, 302) # Should redirect on successful unlinking
        self.assertFalse(DocumentationAlertGroup.objects.filter(pk=self.doc_alert_group_link.pk).exists())
        self.assertRedirects(response, reverse('alerts:alert-detail', args=[self.alert_group.fingerprint]))

        # Check for success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f'Alert unlinked from "{self.documentation.title}" documentation.')

    def test_unlink_documentation_from_alert_view_post_ajax(self):
        self.client.login(username='testuser', password='testpassword')
        self.assertTrue(DocumentationAlertGroup.objects.filter(pk=self.doc_alert_group_link.pk).exists())
        response = self.client.post(self.unlink_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertFalse(DocumentationAlertGroup.objects.filter(pk=self.doc_alert_group_link.pk).exists())

        # Messages are not typically handled for AJAX responses in the same way,
        # so we don't assert for them here.