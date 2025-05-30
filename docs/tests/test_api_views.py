from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model

from docs.models import AlertDocumentation, DocumentationAlertGroup
from alerts.models import AlertGroup

User = get_user_model()

class DocumentationViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpassword', email='admin@example.com')
        self.client.force_authenticate(user=self.user)

        self.doc1 = AlertDocumentation.objects.create(
            title='Doc A', description='<p>Description A</p>', created_by=self.user
        )
        self.doc2 = AlertDocumentation.objects.create(
            title='Doc B', description='<p>Description B</p>', created_by=self.user
        )
        self.list_url = reverse('documentation-list') # 'documentation' is the basename in docs/api/urls.py

    def test_list_documentation_authenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['title'], 'Doc A')
        self.assertEqual(response.data['results'][1]['title'], 'Doc B')

    def test_list_documentation_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_documentation_authenticated(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'New API Doc',
            'description': '<p>Description for new API doc</p>'
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AlertDocumentation.objects.count(), 3)
        self.assertEqual(AlertDocumentation.objects.get(title='New API Doc').created_by, self.user)
        self.assertEqual(response.data['title'], 'New API Doc')

    def test_create_documentation_unauthenticated(self):
        self.client.force_authenticate(user=None)
        data = {
            'title': 'Unauthorized Doc',
            'description': '<p>Description</p>'
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # DRF returns 403 for unauthenticated POST with IsAuthenticated
        self.assertEqual(AlertDocumentation.objects.count(), 2) # No new doc created

    def test_retrieve_documentation_authenticated(self):
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('documentation-detail', kwargs={'pk': self.doc1.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.doc1.title)

    def test_retrieve_documentation_unauthenticated(self):
        self.client.force_authenticate(user=None)
        detail_url = reverse('documentation-detail', kwargs={'pk': self.doc1.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_documentation_authenticated(self):
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('documentation-detail', kwargs={'pk': self.doc1.pk})
        updated_data = {
            'title': 'Updated Doc A',
            'description': '<p>Updated Description A</p>'
        }
        response = self.client.put(detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doc1.refresh_from_db()
        self.assertEqual(self.doc1.title, 'Updated Doc A')
        self.assertEqual(self.doc1.description, '<p>Updated Description A</p>')

    def test_update_documentation_unauthenticated(self):
        self.client.force_authenticate(user=None)
        detail_url = reverse('documentation-detail', kwargs={'pk': self.doc1.pk})
        updated_data = {
            'title': 'Unauthorized Update',
            'description': '<p>Description</p>'
        }
        response = self.client.put(detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.doc1.refresh_from_db()
        self.assertEqual(self.doc1.title, 'Doc A') # Should not be updated

    def test_delete_documentation_authenticated(self):
        self.client.force_authenticate(user=self.user)
        delete_url = reverse('documentation-detail', kwargs={'pk': self.doc1.pk})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AlertDocumentation.objects.count(), 1) # Only doc2 remains

    def test_delete_documentation_unauthenticated(self):
        self.client.force_authenticate(user=None)
        delete_url = reverse('documentation-detail', kwargs={'pk': self.doc1.pk})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(AlertDocumentation.objects.count(), 2) # No doc deleted


class AlertDocumentationLinkViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpassword', email='admin@example.com')
        self.client.force_authenticate(user=self.user)

        self.doc1 = AlertDocumentation.objects.create(
            title='Doc A', description='<p>Description A</p>', created_by=self.user
        )
        self.doc2 = AlertDocumentation.objects.create(
            title='Doc B', description='<p>Description B</p>', created_by=self.user
        )
        self.alert_group1 = AlertGroup.objects.create(
            fingerprint='fp1', name='Alert 1', labels={'job': 'test'}, severity='critical', current_status='firing'
        )
        self.alert_group2 = AlertGroup.objects.create(
            fingerprint='fp2', name='Alert 2', labels={'job': 'test'}, severity='warning', current_status='firing'
        )

        self.link1 = DocumentationAlertGroup.objects.create(
            documentation=self.doc1, alert_group=self.alert_group1, linked_by=self.user
        )
        self.link2 = DocumentationAlertGroup.objects.create(
            documentation=self.doc2, alert_group=self.alert_group1, linked_by=self.user
        )
        self.link3 = DocumentationAlertGroup.objects.create(
            documentation=self.doc1, alert_group=self.alert_group2, linked_by=self.user
        )

        self.list_url = reverse('documentationalertgroup-list') # 'documentationalertgroup' is the basename

    def test_list_links_authenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_list_links_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_links_filter_by_documentation_id(self):
        response = self.client.get(self.list_url, {'documentation_id': self.doc1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertTrue(all(item['documentation'] == self.doc1.pk for item in response.data['results']))

    def test_list_links_filter_by_alert_id(self):
        response = self.client.get(self.list_url, {'alert_id': self.alert_group1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertTrue(all(item['alert_group'] == self.alert_group1.pk for item in response.data['results']))

    def test_list_links_ordering(self):
        # Links are ordered by -linked_at, so link3 (most recent) should be first
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming link3 was created last, then link2, then link1
        self.assertEqual(response.data['results'][0]['id'], self.link3.pk)
        self.assertEqual(response.data['results'][1]['id'], self.link2.pk)
        self.assertEqual(response.data['results'][2]['id'], self.link1.pk)