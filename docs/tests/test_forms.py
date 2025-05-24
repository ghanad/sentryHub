from django.test import TestCase
from docs.forms import AlertDocumentationForm, DocumentationSearchForm
from docs.models import AlertDocumentation

class AlertDocumentationFormTest(TestCase):
    def test_valid_data(self):
        form = AlertDocumentationForm(data={
            'title': 'Test Alert Title',
            'description': 'This is a test description.'
        })
        self.assertTrue(form.is_valid())
        
    def test_missing_title(self):
        form = AlertDocumentationForm(data={
            'description': 'This is a test description.'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        
    def test_missing_description(self):
        form = AlertDocumentationForm(data={
            'title': 'Test Alert Title'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)

    def test_save_form(self):
        form = AlertDocumentationForm(data={
            'title': 'Another Test Title',
            'description': 'Another test description.'
        })
        self.assertTrue(form.is_valid())
        alert_doc = form.save()
        self.assertEqual(AlertDocumentation.objects.count(), 1)
        self.assertEqual(alert_doc.title, 'Another Test Title')
        self.assertEqual(alert_doc.description, 'Another test description.')

class DocumentationSearchFormTest(TestCase):
    def test_valid_query_data(self):
        form = DocumentationSearchForm(data={'query': 'search term'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['query'], 'search term')

    def test_empty_query_data(self):
        form = DocumentationSearchForm(data={'query': ''})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['query'], '')

    def test_no_data(self):
        form = DocumentationSearchForm(data={})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['query'], '')