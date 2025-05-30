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