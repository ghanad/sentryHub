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