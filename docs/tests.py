from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.utils import IntegrityError
from datetime import timedelta

from alerts.models import AlertGroup # Assuming alerts app is at the root
from docs.models import AlertDocumentation, DocumentationAlertGroup

class AlertDocumentationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='doc_test_user', 
            password='password123',
            email='doc_test@example.com'
        )
        self.doc1_data = {
            'title': 'CPU Usage Documentation',
            'description': '<p>This document explains <b>CPU usage</b> alerts.</p>',
            'created_by': self.user
        }
        self.doc2_data = { # For ordering test
            'title': 'Memory Usage Documentation',
            'description': 'Details about memory alerts.',
            'created_by': self.user
        }

    def test_alert_documentation_creation(self):
        doc = AlertDocumentation.objects.create(**self.doc1_data)
        self.assertIsNotNone(doc.pk)
        self.assertEqual(doc.title, self.doc1_data['title'])
        self.assertEqual(doc.description, self.doc1_data['description'])
        self.assertEqual(doc.created_by, self.user)
        self.assertIsNotNone(doc.created_at)
        self.assertIsNotNone(doc.updated_at)
        self.assertTrue(doc.created_at <= doc.updated_at)

    def test_alert_documentation_str_method(self):
        doc = AlertDocumentation.objects.create(**self.doc1_data)
        self.assertEqual(str(doc), self.doc1_data['title'])

    def test_alert_documentation_ordering(self):
        # Create in a specific order to test default ordering by title
        doc2 = AlertDocumentation.objects.create(**self.doc2_data) # Memory...
        doc1 = AlertDocumentation.objects.create(**self.doc1_data) # CPU...
        
        docs = AlertDocumentation.objects.all()
        # Ordering is by title, so doc1_data.title ("CPU...") should come before doc2_data.title ("Memory...")
        self.assertEqual(docs[0].title, self.doc1_data['title'])
        self.assertEqual(docs[1].title, self.doc2_data['title'])

    def test_alert_documentation_field_help_text(self):
        title_help_text = AlertDocumentation._meta.get_field('title').help_text
        description_help_text = AlertDocumentation._meta.get_field('description').help_text
        self.assertEqual(title_help_text, 'A concise and descriptive title for the documentation.')
        self.assertEqual(description_help_text, 'The main content of the documentation. Supports HTML for rich formatting.')

    def test_alert_documentation_description_can_store_html(self):
        html_content = "<h1>Title</h1><ul><li>Point 1</li></ul><script>alert('xss')</script>"
        doc = AlertDocumentation.objects.create(
            title="HTML Test", 
            description=html_content, 
            created_by=self.user
        )
        self.assertEqual(doc.description, html_content) 

    def test_alert_documentation_created_by_can_be_null_on_user_delete(self):
        user_to_delete = User.objects.create_user(username='tempuser', password='password')
        doc = AlertDocumentation.objects.create(
            title="Doc by temp user",
            description="Content",
            created_by=user_to_delete
        )
        self.assertEqual(doc.created_by, user_to_delete)
        
        user_to_delete.delete()
        doc.refresh_from_db()
        self.assertIsNone(doc.created_by)

    def test_documentation_alert_group_creation(self):
        link = DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc1,
            alert_group=self.alert_group1,
            linked_by=self.user1
        )
        self.assertIsNotNone(link.pk)
        self.assertEqual(link.documentation, self.alert_doc1)
        self.assertEqual(link.alert_group, self.alert_group1)
        self.assertEqual(link.linked_by, self.user1)
        self.assertIsNotNone(link.linked_at)

    def test_documentation_alert_group_str_method(self):
        link = DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc1,
            alert_group=self.alert_group1,
            linked_by=self.user1
        )
        expected_str = f"Doc: '{self.alert_doc1.title}' linked to AlertGroup: '{self.alert_group1.name}'"
        self.assertEqual(str(link), expected_str)

    def test_documentation_alert_group_unique_together_constraint(self):
        # Create an initial link
        DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc1,
            alert_group=self.alert_group1,
            linked_by=self.user1
        )
        # Attempt to create a duplicate link
        with self.assertRaises(IntegrityError):
            DocumentationAlertGroup.objects.create(
                documentation=self.alert_doc1, # Same doc
                alert_group=self.alert_group1, # Same alert group
                linked_by=self.user2 # Different user, but constraint is on (documentation, alert_group)
            )

    def test_documentation_alert_group_cascade_delete_documentation(self):
        link = DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc1,
            alert_group=self.alert_group1,
            linked_by=self.user1
        )
        link_pk = link.pk
        self.assertTrue(DocumentationAlertGroup.objects.filter(pk=link_pk).exists())
        
        self.alert_doc1.delete() # Delete the AlertDocumentation
        
        self.assertFalse(DocumentationAlertGroup.objects.filter(pk=link_pk).exists())

    def test_documentation_alert_group_cascade_delete_alert_group(self):
        link = DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc1,
            alert_group=self.alert_group1,
            linked_by=self.user1
        )
        link_pk = link.pk
        self.assertTrue(DocumentationAlertGroup.objects.filter(pk=link_pk).exists())
        
        self.alert_group1.delete() # Delete the AlertGroup
        
        self.assertFalse(DocumentationAlertGroup.objects.filter(pk=link_pk).exists())

    def test_documentation_alert_group_set_null_on_user_delete(self):
        user_to_delete = User.objects.create_user(username='tempuser_for_link', password='password')
        link = DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc1,
            alert_group=self.alert_group1,
            linked_by=user_to_delete
        )
        self.assertEqual(link.linked_by, user_to_delete)
        
        user_to_delete.delete() # Delete the user who linked
        link.refresh_from_db()
        
        self.assertIsNone(link.linked_by)

    def test_documentation_alert_group_ordering(self):
        # Create links in a specific order to test default ordering by -linked_at
        link1 = DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc1, alert_group=self.alert_group1, linked_by=self.user1
        )
        # Ensure a time difference for ordering
        link1.linked_at = timezone.now() - timedelta(minutes=1)
        link1.save()

        link2 = DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc2, alert_group=self.alert_group2, linked_by=self.user2
        )
        # link2.linked_at will be later than link1.linked_at

        links = DocumentationAlertGroup.objects.all()
        # Default ordering is by '-linked_at' (most recent first)
        self.assertEqual(links[0], link2)
        self.assertEqual(links[1], link1)

class DocumentationAlertGroupModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='doclinkuser1', password='password123')
        self.user2 = User.objects.create_user(username='doclinkuser2', password='password456')

        self.alert_doc1 = AlertDocumentation.objects.create(
            title='Doc 1 for Linking',
            description='Content for Doc 1',
            created_by=self.user1
        )
        self.alert_doc2 = AlertDocumentation.objects.create(
            title='Doc 2 for Linking',
            description='Content for Doc 2',
            created_by=self.user1
        )

        self.alert_group1 = AlertGroup.objects.create(
            fingerprint='fp-doclink-ag1',
            name='Alert Group 1 for Doc Linking',
            severity='critical',
            current_status='firing'
        )
        self.alert_group2 = AlertGroup.objects.create(
            fingerprint='fp-doclink-ag2',
            name='Alert Group 2 for Doc Linking',
            severity='warning',
            current_status='resolved'
        )

from tinymce.widgets import TinyMCE
from django import forms as django_forms # To avoid confusion with local 'forms' module if any
from docs.forms import AlertDocumentationForm, DocumentationSearchForm

class AlertDocumentationFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='form_test_user', password='password123')
        self.valid_data = {
            'title': 'Test Document Title',
            'description': '<p>This is a test description.</p>'
        }

    def test_alert_documentation_form_valid_data(self):
        form = AlertDocumentationForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")
        
        # Test saving the form
        instance = form.save(commit=False)
        # created_by would typically be set in the view before final save
        instance.created_by = self.user 
        instance.save()
        
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.title, self.valid_data['title'])
        self.assertEqual(instance.description, self.valid_data['description'])
        self.assertEqual(instance.created_by, self.user)

    def test_alert_documentation_form_missing_title(self):
        invalid_data = self.valid_data.copy()
        del invalid_data['title']
        form = AlertDocumentationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('This field is required.', form.errors['title'])

    def test_alert_documentation_form_missing_description(self):
        # HTMLField (TinyMCE) is typically required by default for ModelForms
        invalid_data = self.valid_data.copy()
        del invalid_data['description']
        form = AlertDocumentationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)
        self.assertIn('This field is required.', form.errors['description'])
        
    def test_alert_documentation_form_widget_configuration(self):
        form = AlertDocumentationForm()
        # Description field widget
        self.assertIsInstance(form.fields['description'].widget, TinyMCE)
        # Title field widget and attributes
        title_widget = form.fields['title'].widget
        self.assertIsInstance(title_widget, django_forms.TextInput) # from django.forms
        self.assertEqual(title_widget.attrs.get('class'), 'form-control')

    def test_alert_documentation_form_help_texts(self):
        form = AlertDocumentationForm()
        self.assertEqual(form.fields['title'].help_text, 'A concise and descriptive title for the documentation.')
        # Description help text comes from model, already tested in model tests.
        # If form overrides it, test here.

    def test_alert_documentation_form_save_commit_false(self):
        form = AlertDocumentationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)
        
        # Check that the instance is not saved to DB yet
        self.assertIsNone(instance.pk, "Instance should not have a PK if commit=False and not yet saved.")
        
        # Set created_by (usually done in view)
        instance.created_by = self.user
        instance.save() # Now save to DB
        
        self.assertIsNotNone(instance.pk, "Instance should have a PK after explicit save.")
        self.assertEqual(instance.title, self.valid_data['title'])
        self.assertEqual(instance.created_by, self.user)


class DocumentationSearchFormTests(TestCase):
    def test_documentation_search_form_valid_query(self):
        form = DocumentationSearchForm(data={'query': 'test search'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['query'], 'test search')

    def test_documentation_search_form_empty_query_is_valid(self):
        # 'query' field has required=False
        form = DocumentationSearchForm(data={'query': ''})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['query'], '')

        form_no_data = DocumentationSearchForm(data={})
        self.assertTrue(form_no_data.is_valid())
        self.assertEqual(form_no_data.cleaned_data.get('query'), None) # Or '' depending on empty_value

    def test_documentation_search_form_widget_configuration(self):
        form = DocumentationSearchForm()
        query_widget = form.fields['query'].widget
        self.assertIsInstance(query_widget, django_forms.TextInput)
        self.assertEqual(query_widget.attrs.get('class'), 'form-control mr-sm-2')
        self.assertEqual(query_widget.attrs.get('placeholder'), 'Search Documentation...')
        self.assertEqual(query_widget.attrs.get('aria-label'), 'Search')

class LinkDocumentationToAlertViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='link_test_user', password='password123')
        self.other_user = User.objects.create_user(username='other_link_user', password='password123')

        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp-link-view', name='Link Test Alert Group', severity='warning'
        )
        self.doc1 = AlertDocumentation.objects.create(title='Doc Alpha', description='Content Alpha', created_by=self.user)
        self.doc2 = AlertDocumentation.objects.create(title='Doc Beta', description='Content Beta', created_by=self.user)
        self.doc_already_linked = AlertDocumentation.objects.create(title='Doc Gamma (Already Linked)', description='...', created_by=self.user)

        # Pre-link one document
        self.existing_link = DocumentationAlertGroup.objects.create(
            documentation=self.doc_already_linked,
            alert_group=self.alert_group,
            linked_by=self.user
        )

        self.link_url = reverse('docs:link-documentation-to-alert', kwargs={'pk': self.alert_group.pk})
        # Assuming the alert detail URL is 'alerts:alert-detail' and uses fingerprint
        self.alert_detail_url = reverse('alerts:alert-detail', kwargs={'fingerprint': self.alert_group.fingerprint})
        self.login_url = settings.LOGIN_URL

    def test_link_view_unauthenticated_get(self):
        response = self.client.get(self.link_url)
        expected_url = f"{self.login_url}?next={self.link_url}"
        self.assertRedirects(response, expected_url)

    def test_link_view_unauthenticated_post(self):
        response = self.client.post(self.link_url, {'documentation_id': self.doc1.pk})
        expected_url = f"{self.login_url}?next={self.link_url}"
        self.assertRedirects(response, expected_url)

    def test_link_view_authenticated_get(self):
        self.client.login(username='link_test_user', password='password123')
        response = self.client.get(self.link_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/link_documentation.html')
        self.assertEqual(response.context['object'], self.alert_group) # or 'alertgroup'
        self.assertEqual(response.context['alertgroup'], self.alert_group)
        
        self.assertIn('documentations', response.context)
        all_docs_in_context = list(response.context['documentations'])
        self.assertEqual(len(all_docs_in_context), 3) # doc1, doc2, doc_already_linked
        self.assertIn(self.doc1, all_docs_in_context)
        self.assertIn(self.doc2, all_docs_in_context)
        self.assertIn(self.doc_already_linked, all_docs_in_context)

        self.assertIn('current_docs', response.context)
        current_docs_in_context = list(response.context['current_docs'])
        self.assertEqual(len(current_docs_in_context), 1)
        self.assertIn(self.doc_already_linked, current_docs_in_context)

    def test_link_view_get_non_existent_alert_group(self):
        self.client.login(username='link_test_user', password='password123')
        non_existent_url = reverse('docs:link-documentation-to-alert', kwargs={'pk': 99999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)

    @patch('django.contrib.messages.success')
    def test_link_view_post_successful_link(self, mock_messages_success):
        self.client.login(username='link_test_user', password='password123')
        self.assertFalse(DocumentationAlertGroup.objects.filter(documentation=self.doc1, alert_group=self.alert_group).exists())
        
        response = self.client.post(self.link_url, {'documentation_id': self.doc1.pk})
        
        self.assertTrue(DocumentationAlertGroup.objects.filter(documentation=self.doc1, alert_group=self.alert_group).exists())
        new_link = DocumentationAlertGroup.objects.get(documentation=self.doc1, alert_group=self.alert_group)
        self.assertEqual(new_link.linked_by, self.user)
        
        self.assertRedirects(response, self.alert_detail_url)
        mock_messages_success.assert_called_once_with(
            response.wsgi_request,
            f'Alert linked to "{self.doc1.title}" documentation.'
        )

    @patch('django.contrib.messages.info')
    def test_link_view_post_already_linked(self, mock_messages_info):
        self.client.login(username='link_test_user', password='password123')
        # doc_already_linked is already linked in setUp
        initial_link_count = DocumentationAlertGroup.objects.filter(alert_group=self.alert_group).count()
        
        response = self.client.post(self.link_url, {'documentation_id': self.doc_already_linked.pk})
        
        self.assertEqual(DocumentationAlertGroup.objects.filter(alert_group=self.alert_group).count(), initial_link_count)
        self.assertRedirects(response, self.alert_detail_url)
        mock_messages_info.assert_called_once_with(
            response.wsgi_request,
            f'Alert was already linked to this documentation.'
        )

    @patch('django.contrib.messages.error')
    def test_link_view_post_missing_documentation_id(self, mock_messages_error):
        self.client.login(username='link_test_user', password='password123')
        response = self.client.post(self.link_url, {}) # No documentation_id
        
        self.assertRedirects(response, self.alert_detail_url) # Redirects back
        mock_messages_error.assert_called_once_with(
            response.wsgi_request,
            "No documentation selected to link."
        )

    def test_link_view_post_non_existent_documentation_id(self):
        self.client.login(username='link_test_user', password='password123')
        response = self.client.post(self.link_url, {'documentation_id': 99999})
        self.assertEqual(response.status_code, 404) # Due to get_object_or_404 for documentation


class UnlinkDocumentationFromAlertViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='unlink_test_user', password='password123')
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp-unlink-view', name='Unlink Test Alert Group', severity='info'
        )
        self.doc_to_unlink = AlertDocumentation.objects.create(
            title='Doc to Unlink', description='...', created_by=self.user
        )
        self.link_to_delete = DocumentationAlertGroup.objects.create(
            documentation=self.doc_to_unlink,
            alert_group=self.alert_group,
            linked_by=self.user
        )
        self.unlink_url = reverse('docs:unlink-documentation-from-alert', kwargs={
            'alert_group_pk': self.alert_group.pk, 
            'documentation_pk': self.doc_to_unlink.pk
        })
        self.alert_detail_url = reverse('alerts:alert-detail', kwargs={'fingerprint': self.alert_group.fingerprint})
        self.login_url = settings.LOGIN_URL

    def test_unlink_view_unauthenticated_post(self):
        response = self.client.post(self.unlink_url)
        expected_url = f"{self.login_url}?next={self.unlink_url}"
        self.assertRedirects(response, expected_url)
        self.assertTrue(DocumentationAlertGroup.objects.filter(pk=self.link_to_delete.pk).exists())

    @patch('django.contrib.messages.success')
    def test_unlink_view_authenticated_post_successful_unlink(self, mock_messages_success):
        self.client.login(username='unlink_test_user', password='password123')
        self.assertTrue(DocumentationAlertGroup.objects.filter(pk=self.link_to_delete.pk).exists())
        
        response = self.client.post(self.unlink_url)
        
        self.assertFalse(DocumentationAlertGroup.objects.filter(pk=self.link_to_delete.pk).exists())
        self.assertRedirects(response, self.alert_detail_url)
        mock_messages_success.assert_called_once_with(
            response.wsgi_request,
            f'Alert unlinked from "{self.doc_to_unlink.title}" documentation.'
        )

    def test_unlink_view_authenticated_post_ajax_successful_unlink(self):
        self.client.login(username='unlink_test_user', password='password123')
        self.assertTrue(DocumentationAlertGroup.objects.filter(pk=self.link_to_delete.pk).exists())
        
        response = self.client.post(self.unlink_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertFalse(DocumentationAlertGroup.objects.filter(pk=self.link_to_delete.pk).exists())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'success'})

    def test_unlink_view_post_link_not_found_alert_group_invalid(self):
        self.client.login(username='unlink_test_user', password='password123')
        non_existent_url = reverse('docs:unlink-documentation-from-alert', kwargs={
            'alert_group_pk': 99999, # Non-existent alert group
            'documentation_pk': self.doc_to_unlink.pk
        })
        response = self.client.post(non_existent_url)
        self.assertEqual(response.status_code, 404) # get_object_or_404 for AlertGroup

    def test_unlink_view_post_link_not_found_doc_invalid(self):
        self.client.login(username='unlink_test_user', password='password123')
        non_existent_url = reverse('docs:unlink-documentation-from-alert', kwargs={
            'alert_group_pk': self.alert_group.pk,
            'documentation_pk': 99999 # Non-existent documentation
        })
        response = self.client.post(non_existent_url)
        self.assertEqual(response.status_code, 404) # get_object_or_404 for DocumentationAlertGroup (link)

    def test_unlink_view_post_link_not_found_no_actual_link(self):
        self.client.login(username='unlink_test_user', password='password123')
        # Create another doc that is not linked to self.alert_group
        other_doc = AlertDocumentation.objects.create(title='Other Unlinked Doc', description='...', created_by=self.user)
        
        url_for_non_linked_doc = reverse('docs:unlink-documentation-from-alert', kwargs={
            'alert_group_pk': self.alert_group.pk,
            'documentation_pk': other_doc.pk 
        })
        response = self.client.post(url_for_non_linked_doc)
        self.assertEqual(response.status_code, 404) # get_object_or_404 for DocumentationAlertGroup (link)

    def test_unlink_view_get_not_allowed(self):
        self.client.login(username='unlink_test_user', password='password123')
        response = self.client.get(self.unlink_url)
        self.assertEqual(response.status_code, 405) # Method Not Allowed

class DocumentationUpdateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='update_test_user', password='password123')
        self.other_user = User.objects.create_user(username='other_user_doc', password='password123')
        
        self.doc_to_update = AlertDocumentation.objects.create(
            title='Initial Title for Update',
            description='Initial description.',
            created_by=self.user
        )
        self.update_url = reverse('docs:documentation-update', kwargs={'pk': self.doc_to_update.pk})
        self.detail_url = reverse('docs:documentation-detail', kwargs={'pk': self.doc_to_update.pk})
        self.login_url = settings.LOGIN_URL

    def test_documentation_update_view_unauthenticated_get(self):
        response = self.client.get(self.update_url)
        expected_redirect_url = f"{self.login_url}?next={self.update_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)

    def test_documentation_update_view_unauthenticated_post(self):
        response = self.client.post(self.update_url, {'title': 'Attempt Update', 'description': '...'})
        expected_redirect_url = f"{self.login_url}?next={self.update_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)

    def test_documentation_update_view_authenticated_get(self):
        self.client.login(username='update_test_user', password='password123')
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/documentation_form.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], AlertDocumentationForm)
        self.assertEqual(response.context['form'].instance, self.doc_to_update)
        self.assertEqual(response.context['form_title'], f"Update Documentation: {self.doc_to_update.title}")
        # Check initial values
        self.assertEqual(response.context['form'].initial['title'], self.doc_to_update.title)
        self.assertEqual(response.context['form'].initial['description'], self.doc_to_update.description)

    def test_documentation_update_view_get_non_existent_pk(self):
        self.client.login(username='update_test_user', password='password123')
        non_existent_url = reverse('docs:documentation-update', kwargs={'pk': 99999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)

    @patch('django.contrib.messages.success')
    def test_documentation_update_view_authenticated_post_valid(self, mock_messages_success):
        self.client.login(username='update_test_user', password='password123')
        updated_data = {
            'title': 'Updated Document Title',
            'description': '<p>Updated description content.</p>'
        }
        response = self.client.post(self.update_url, updated_data)
        
        self.doc_to_update.refresh_from_db()
        self.assertEqual(self.doc_to_update.title, updated_data['title'])
        self.assertEqual(self.doc_to_update.description, updated_data['description'])
        self.assertEqual(self.doc_to_update.created_by, self.user) # Should not change
        
        self.assertRedirects(response, self.detail_url, fetch_redirect_response=False)
        mock_messages_success.assert_called_once_with(
            response.wsgi_request,
            f'Documentation "{self.doc_to_update.title}" updated successfully.'
        )

    def test_documentation_update_view_authenticated_post_invalid(self):
        self.client.login(username='update_test_user', password='password123')
        original_title = self.doc_to_update.title
        invalid_data = {
            'title': '', # Empty title
            'description': 'Description remains.'
        }
        response = self.client.post(self.update_url, invalid_data)
        
        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertTemplateUsed(response, 'docs/documentation_form.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('title', response.context['form'].errors)
        
        self.doc_to_update.refresh_from_db()
        self.assertEqual(self.doc_to_update.title, original_title) # Title should not have changed


class DocumentationDeleteViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='delete_test_user', password='password123')
        
        self.doc_to_delete = AlertDocumentation.objects.create(
            title='Document to Delete',
            description='This will be deleted.',
            created_by=self.user
        )
        self.delete_url = reverse('docs:documentation-delete', kwargs={'pk': self.doc_to_delete.pk})
        self.list_url = reverse('docs:documentation-list')
        self.login_url = settings.LOGIN_URL

        # Create related DocumentationAlertGroup to test cascade delete
        self.alert_group_linked = AlertGroup.objects.create(fingerprint='fp_delete_view_test', name='AG for Delete Test')
        self.link = DocumentationAlertGroup.objects.create(
            documentation=self.doc_to_delete,
            alert_group=self.alert_group_linked,
            linked_by=self.user
        )

    def test_documentation_delete_view_unauthenticated_get(self):
        response = self.client.get(self.delete_url)
        expected_redirect_url = f"{self.login_url}?next={self.delete_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)

    def test_documentation_delete_view_unauthenticated_post(self):
        response = self.client.post(self.delete_url)
        expected_redirect_url = f"{self.login_url}?next={self.delete_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)
        self.assertTrue(AlertDocumentation.objects.filter(pk=self.doc_to_delete.pk).exists())


    def test_documentation_delete_view_authenticated_get(self):
        self.client.login(username='delete_test_user', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/documentation_confirm_delete.html')
        self.assertIn('object', response.context) # Default context object name for DeleteView
        self.assertEqual(response.context['object'], self.doc_to_delete)
        self.assertContains(response, f"Are you sure you want to delete the documentation: &quot;{self.doc_to_delete.title}&quot;?")

    def test_documentation_delete_view_get_non_existent_pk(self):
        self.client.login(username='delete_test_user', password='password123')
        non_existent_url = reverse('docs:documentation-delete', kwargs={'pk': 99999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)

    @patch('django.contrib.messages.success')
    def test_documentation_delete_view_authenticated_post_confirm_delete(self, mock_messages_success):
        self.client.login(username='delete_test_user', password='password123')
        doc_pk_to_delete = self.doc_to_delete.pk
        link_pk_to_delete = self.link.pk
        
        self.assertTrue(AlertDocumentation.objects.filter(pk=doc_pk_to_delete).exists())
        self.assertTrue(DocumentationAlertGroup.objects.filter(pk=link_pk_to_delete).exists())

        response = self.client.post(self.delete_url)
        
        self.assertFalse(AlertDocumentation.objects.filter(pk=doc_pk_to_delete).exists())
        self.assertFalse(DocumentationAlertGroup.objects.filter(pk=link_pk_to_delete).exists()) # Check cascade delete
        
        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        mock_messages_success.assert_called_once_with(
            response.wsgi_request,
            f'Documentation "{self.doc_to_delete.title}" deleted successfully.'
        )

from django.test import Client # Client is already imported via TestCase
from django.urls import reverse
from django.conf import settings
from django.contrib.messages import get_messages

# --- View Tests ---

class DocumentationListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='view_test_user', password='password123')
        self.list_url = reverse('docs:documentation-list')

        self.doc1 = AlertDocumentation.objects.create(
            title='CPU Alerting Guide', 
            description='How to handle CPU alerts.', 
            created_by=self.user
        )
        self.doc2 = AlertDocumentation.objects.create(
            title='Memory Alerting Guide', 
            description='How to handle Memory alerts. Includes details on CPU.', # For search test
            created_by=self.user
        )
        self.doc3 = AlertDocumentation.objects.create(
            title='Network Troubleshooting', 
            description='Troubleshooting network issues.', 
            created_by=self.user
        )
        
        # For linked_alerts_count
        self.ag1 = AlertGroup.objects.create(fingerprint='fp_doc_list_ag1', name='AG1')
        DocumentationAlertGroup.objects.create(documentation=self.doc1, alert_group=self.ag1, linked_by=self.user)


    def test_documentation_list_view_unauthenticated(self):
        response = self.client.get(self.list_url)
        expected_redirect_url = f"{settings.LOGIN_URL}?next={self.list_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)

    def test_documentation_list_view_authenticated_get(self):
        self.client.login(username='view_test_user', password='password123')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/documentation_list.html')
        self.assertIn('documentations', response.context)
        self.assertEqual(len(response.context['documentations']), 3)
        self.assertIn('search_form', response.context)
        self.assertIsInstance(response.context['search_form'], DocumentationSearchForm)
        self.assertEqual(response.context['search_query'], '') # Default empty

        # Test linked_alerts_count annotation
        doc1_from_context = response.context['documentations'].get(pk=self.doc1.pk)
        self.assertEqual(doc1_from_context.linked_alerts_count, 1)
        doc2_from_context = response.context['documentations'].get(pk=self.doc2.pk)
        self.assertEqual(doc2_from_context.linked_alerts_count, 0)
        
        # Test default ordering by title (CPU, Memory, Network)
        titles_in_order = [doc.title for doc in response.context['documentations']]
        self.assertEqual(titles_in_order, ['CPU Alerting Guide', 'Memory Alerting Guide', 'Network Troubleshooting'])


    def test_documentation_list_view_search_title(self):
        self.client.login(username='view_test_user', password='password123')
        response = self.client.get(self.list_url, {'query': 'CPU Alerting'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('documentations', response.context)
        self.assertEqual(len(response.context['documentations']), 1)
        self.assertEqual(response.context['documentations'][0], self.doc1)
        self.assertEqual(response.context['search_query'], 'CPU Alerting')

    def test_documentation_list_view_search_description(self):
        self.client.login(username='view_test_user', password='password123')
        response = self.client.get(self.list_url, {'query': 'handle Memory'}) # In doc2 description
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['documentations']), 1)
        self.assertEqual(response.context['documentations'][0], self.doc2)

    def test_documentation_list_view_search_no_results(self):
        self.client.login(username='view_test_user', password='password123')
        response = self.client.get(self.list_url, {'query': 'nonexistentqueryxyz'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['documentations']), 0)
        self.assertContains(response, "No documentation entries found matching your query.")

    def test_documentation_list_view_pagination(self):
        self.client.login(username='view_test_user', password='password123')
        # Create more than paginate_by (default 10 for ListView)
        for i in range(15):
            AlertDocumentation.objects.create(
                title=f'Doc Page Test {i}', 
                description=f'Desc for {i}', 
                created_by=self.user
            )
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('documentations', response.context)
        self.assertIn('is_paginated', response.context)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['documentations']), 10) # Default page size

        response_page2 = self.client.get(self.list_url, {'page': 2})
        self.assertEqual(response_page2.status_code, 200)
        # 3 from setUp + 15 new = 18 total. Page 1 has 10, Page 2 has 8.
        self.assertEqual(len(response_page2.context['documentations']), 8)


class DocumentationDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='detail_test_user', password='password123')
        self.doc = AlertDocumentation.objects.create(
            title='Detailed Doc', 
            description='Very detailed content.', 
            created_by=self.user
        )
        self.detail_url = reverse('docs:documentation-detail', kwargs={'pk': self.doc.pk})

        # Linked AlertGroups
        self.ag1 = AlertGroup.objects.create(fingerprint='fp_detail_ag1', name='AG Detail 1', last_occurrence=timezone.now() - timedelta(hours=1))
        self.ag2 = AlertGroup.objects.create(fingerprint='fp_detail_ag2', name='AG Detail 2', last_occurrence=timezone.now()) # More recent
        DocumentationAlertGroup.objects.create(documentation=self.doc, alert_group=self.ag1, linked_by=self.user)
        DocumentationAlertGroup.objects.create(documentation=self.doc, alert_group=self.ag2, linked_by=self.user)


    def test_documentation_detail_view_unauthenticated(self):
        response = self.client.get(self.detail_url)
        expected_redirect_url = f"{settings.LOGIN_URL}?next={self.detail_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)

    def test_documentation_detail_view_authenticated_get(self):
        self.client.login(username='detail_test_user', password='password123')
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/documentation_detail.html')
        self.assertIn('documentation', response.context)
        self.assertEqual(response.context['documentation'], self.doc)
        
        self.assertIn('linked_alerts', response.context)
        linked_alerts_in_context = response.context['linked_alerts']
        self.assertEqual(linked_alerts_in_context.count(), 2)
        self.assertIn(self.ag1, linked_alerts_in_context)
        self.assertIn(self.ag2, linked_alerts_in_context)
        # Check ordering by -last_occurrence
        self.assertEqual(list(linked_alerts_in_context), [self.ag2, self.ag1])


    def test_documentation_detail_view_non_existent_pk(self):
        self.client.login(username='detail_test_user', password='password123')
        non_existent_url = reverse('docs:documentation-detail', kwargs={'pk': 99999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)


class DocumentationCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='create_test_user', password='password123')
        self.create_url = reverse('docs:documentation-create')
        self.list_url = reverse('docs:documentation-list') # For redirect check after successful creation

    def test_documentation_create_view_unauthenticated_get(self):
        response = self.client.get(self.create_url)
        expected_redirect_url = f"{settings.LOGIN_URL}?next={self.create_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)
        
    def test_documentation_create_view_unauthenticated_post(self):
        response = self.client.post(self.create_url, {'title': 'test', 'description': 'test'})
        expected_redirect_url = f"{settings.LOGIN_URL}?next={self.create_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)

    def test_documentation_create_view_authenticated_get(self):
        self.client.login(username='create_test_user', password='password123')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/documentation_form.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], AlertDocumentationForm)
        self.assertEqual(response.context['form_title'], "Create New Documentation")

    def test_documentation_create_view_get_prefill_title(self):
        self.client.login(username='create_test_user', password='password123')
        alert_name = "My Alert Name Needs Docs"
        response = self.client.get(self.create_url, {'alert_name': alert_name})
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], AlertDocumentationForm)
        # Assuming unquote is used by the view:
        self.assertEqual(response.context['form'].initial.get('title'), alert_name)

    @patch('django.contrib.messages.success') # Mock messages.success
    def test_documentation_create_view_authenticated_post_valid(self, mock_messages_success):
        self.client.login(username='create_test_user', password='password123')
        valid_data = {
            'title': 'New Doc Valid Title',
            'description': 'Valid description content.'
        }
        response = self.client.post(self.create_url, valid_data)
        
        self.assertEqual(AlertDocumentation.objects.count(), 1)
        new_doc = AlertDocumentation.objects.first()
        self.assertEqual(new_doc.title, valid_data['title'])
        self.assertEqual(new_doc.description, valid_data['description'])
        self.assertEqual(new_doc.created_by, self.user) # Check created_by is set
        
        expected_detail_url = reverse('docs:documentation-detail', kwargs={'pk': new_doc.pk})
        self.assertRedirects(response, expected_detail_url, fetch_redirect_response=False)
        
        mock_messages_success.assert_called_once_with(
            response.wsgi_request, # The request object from the response
            f'Documentation "{new_doc.title}" created successfully.'
        )

    def test_documentation_create_view_authenticated_post_invalid(self):
        self.client.login(username='create_test_user', password='password123')
        invalid_data = {
            'title': '', # Missing title
            'description': 'Some description.'
        }
        response = self.client.post(self.create_url, invalid_data)
        
        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertTemplateUsed(response, 'docs/documentation_form.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors) # Form has errors
        self.assertIn('title', response.context['form'].errors)
        self.assertEqual(AlertDocumentation.objects.count(), 0) # No object created

from unittest.mock import patch
import logging

from docs.services.documentation_matcher import match_documentation_to_alert, get_documentation_for_alert

class DocumentationMatcherServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='matcher_user', password='password123')
        self.alert_group_cpu = AlertGroup.objects.create(
            fingerprint='fp-cpu-high',
            name='High CPU Usage',
            severity='critical'
        )
        self.alert_group_mem = AlertGroup.objects.create(
            fingerprint='fp-mem-high',
            name='High Memory Usage',
            severity='warning'
        )
        self.doc_cpu = AlertDocumentation.objects.create(
            title='High CPU Usage', # Exact match for alert_group_cpu.name
            description='Documentation for high CPU usage.',
            created_by=self.user
        )
        self.doc_cpu_lower = AlertDocumentation.objects.create(
            title='high cpu usage', # Lowercase match
            description='Lowercase doc for high CPU.',
            created_by=self.user
        )
        self.doc_other = AlertDocumentation.objects.create(
            title='Network Latency Issue',
            description='Documentation for network problems.',
            created_by=self.user
        )

    # --- Tests for match_documentation_to_alert ---
    def test_match_documentation_found_and_link_created(self):
        matched_doc = match_documentation_to_alert(self.alert_group_cpu, self.user)
        self.assertEqual(matched_doc, self.doc_cpu)
        
        link_exists = DocumentationAlertGroup.objects.filter(
            documentation=self.doc_cpu,
            alert_group=self.alert_group_cpu
        ).exists()
        self.assertTrue(link_exists)
        
        link = DocumentationAlertGroup.objects.get(
            documentation=self.doc_cpu,
            alert_group=self.alert_group_cpu
        )
        self.assertEqual(link.linked_by, self.user)
        self.assertIsNotNone(link.linked_at)

    def test_match_documentation_no_match_by_title(self):
        # alert_group_mem.name is 'High Memory Usage', no doc with this exact title
        matched_doc = match_documentation_to_alert(self.alert_group_mem, self.user)
        self.assertIsNone(matched_doc)
        link_exists = DocumentationAlertGroup.objects.filter(
            alert_group=self.alert_group_mem
        ).exists()
        self.assertFalse(link_exists)

    def test_match_documentation_already_linked(self):
        # Pre-create the link
        existing_link = DocumentationAlertGroup.objects.create(
            documentation=self.doc_cpu,
            alert_group=self.alert_group_cpu,
            linked_by=self.user
        )
        initial_link_count = DocumentationAlertGroup.objects.count()

        matched_doc = match_documentation_to_alert(self.alert_group_cpu, self.user)
        self.assertEqual(matched_doc, self.doc_cpu)
        
        # Verify no new link was created, count should be the same
        self.assertEqual(DocumentationAlertGroup.objects.count(), initial_link_count)
        
        # Verify the existing link's linked_at or linked_by wasn't unnecessarily updated
        # (get_or_create behavior: if exists, it returns the existing one, no update)
        link_after_match = DocumentationAlertGroup.objects.get(pk=existing_link.pk)
        self.assertEqual(link_after_match.linked_at, existing_link.linked_at)


    def test_match_documentation_case_sensitive(self):
        # alert_group_cpu.name = "High CPU Usage"
        # doc_cpu_lower.title = "high cpu usage"
        # Default filter is case-sensitive
        matched_doc = match_documentation_to_alert(self.alert_group_cpu, self.user, match_case_sensitive=True)
        self.assertEqual(matched_doc, self.doc_cpu) # Should match the exact case one
        
        # Clean up any potential link from the previous match to test the lowercase one
        DocumentationAlertGroup.objects.all().delete()
        
        # If we want to test that it *doesn't* match the lowercase one when case sensitive is implied
        # and an exact match exists, that's covered by the above.
        # If we want to test that it *would* match lowercase if exact wasn't there,
        # we'd need to remove the exact match doc or change alert_group name.
        
        # Test direct matching against the lowercase title with case-insensitive logic in service
        # Create a new alert group that should only match the lowercase doc if matching is case-insensitive
        alert_group_cpu_lower_name = AlertGroup.objects.create(
            fingerprint='fp-cpu-lower-name',
            name='high cpu usage', # Name matches doc_cpu_lower.title
            severity='critical'
        )
        matched_doc_lower = match_documentation_to_alert(alert_group_cpu_lower_name, self.user, match_case_sensitive=False)
        self.assertEqual(matched_doc_lower, self.doc_cpu_lower)

        matched_doc_sensitive = match_documentation_to_alert(alert_group_cpu_lower_name, self.user, match_case_sensitive=True)
        self.assertEqual(matched_doc_sensitive, self.doc_cpu_lower) # Exact match here as well


    @patch('docs.services.documentation_matcher.logger')
    def test_match_documentation_filter_exception(self, mock_logger):
        with patch('docs.models.AlertDocumentation.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error during filter")
            matched_doc = match_documentation_to_alert(self.alert_group_cpu, self.user)
            self.assertIsNone(matched_doc)
            mock_logger.error.assert_called_once()
            self.assertIn("Error filtering AlertDocumentation", mock_logger.error.call_args[0][0])

    @patch('docs.services.documentation_matcher.logger')
    def test_match_documentation_get_or_create_exception(self, mock_logger):
        # Ensure a doc exists that will be found by filter
        with patch('docs.models.DocumentationAlertGroup.objects.get_or_create') as mock_get_or_create:
            mock_get_or_create.side_effect = Exception("Database error during get_or_create")
            matched_doc = match_documentation_to_alert(self.alert_group_cpu, self.user) # self.doc_cpu matches its name
            self.assertIsNone(matched_doc) # Should return None as the linking failed
            mock_logger.error.assert_called_once()
            self.assertIn("Error linking documentation", mock_logger.error.call_args[0][0])

    # --- Tests for get_documentation_for_alert ---
    def test_get_documentation_linked(self):
        # Link doc_cpu and doc_other to alert_group_cpu
        DocumentationAlertGroup.objects.create(documentation=self.doc_cpu, alert_group=self.alert_group_cpu, linked_by=self.user)
        DocumentationAlertGroup.objects.create(documentation=self.doc_other, alert_group=self.alert_group_cpu, linked_by=self.user)
        
        linked_docs = get_documentation_for_alert(self.alert_group_cpu)
        self.assertEqual(linked_docs.count(), 2)
        self.assertIn(self.doc_cpu, linked_docs)
        self.assertIn(self.doc_other, linked_docs)

    def test_get_documentation_no_links(self):
        linked_docs = get_documentation_for_alert(self.alert_group_mem) # No docs linked to this group
        self.assertEqual(linked_docs.count(), 0)
        self.assertFalse(linked_docs.exists())
        
    @patch('docs.services.documentation_matcher.logger')
    def test_get_documentation_exception(self, mock_logger):
        with patch.object(AlertGroup, 'alertdocumentation_set', side_effect=Exception("DB Error on related manager")):
            linked_docs = get_documentation_for_alert(self.alert_group_cpu)
            self.assertEqual(linked_docs.count(), 0) # Should return empty queryset on error
            mock_logger.error.assert_called_once()
            self.assertIn("Error fetching documentation for alert", mock_logger.error.call_args[0][0])
