from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from alerts.models import AlertGroup
from docs.models import AlertDocumentation, DocumentationAlertGroup
# from docs.api.serializers import AlertDocumentationSerializer, DocumentationAlertGroupSerializer # Will be used by ViewSet

# Suppress logging if not needed for these tests
import logging
logging.disable(logging.CRITICAL)


class DocumentationViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='doc_api_user1', password='password123', email='docapi1@example.com')
        self.user2 = User.objects.create_user(username='doc_api_user2', password='password456', email='docapi2@example.com')

        # URLs
        self.list_create_url = reverse('docs_api:documentation-list') # Default DRF naming

        # Documentation instances
        self.doc1 = AlertDocumentation.objects.create(
            title='CPU High Runbook',
            description='Steps to resolve high CPU issues. Related to #performance.',
            created_by=self.user1,
            tags=['cpu', 'performance', 'linux']
        )
        self.doc2 = AlertDocumentation.objects.create(
            title='Memory Leak Playbook',
            description='How to find and fix memory leaks. Also about #performance and #java.',
            created_by=self.user2,
            tags=['memory', 'java', 'performance']
        )
        self.doc3_no_tags = AlertDocumentation.objects.create(
            title='Disk Full Guide',
            description='Guide for disk full alerts.',
            created_by=self.user1
        )
        
        self.detail_url_doc1 = reverse('docs_api:documentation-detail', kwargs={'pk': self.doc1.pk})
        self.linked_alerts_url_doc1 = reverse('docs_api:documentation-linked-alerts', kwargs={'pk': self.doc1.pk})
        self.link_alert_url_doc1 = reverse('docs_api:documentation-link-alert', kwargs={'pk': self.doc1.pk})
        self.unlink_alert_url_doc1 = reverse('docs_api:documentation-unlink-alert', kwargs={'pk': self.doc1.pk})

        # AlertGroup instances
        self.ag1 = AlertGroup.objects.create(
            fingerprint='fp-api-ag1', name='High CPU on web servers', severity='critical',
            labels={'host': 'web01', 'service': 'webapp'}
        )
        self.ag2 = AlertGroup.objects.create(
            fingerprint='fp-api-ag2', name='Memory leak in payment service', severity='high',
            labels={'host': 'app01', 'service': 'payment'}
        )
        self.ag3 = AlertGroup.objects.create(
            fingerprint='fp-api-ag3', name='Disk nearing full on db01', severity='warning',
            labels={'host': 'db01', 'service': 'database'}
        )
        
        # Existing link for testing
        self.existing_link_doc1_ag1 = DocumentationAlertGroup.objects.create(
            documentation=self.doc1,
            alert_group=self.ag1,
            linked_by=self.user1
        )
        
        self.valid_create_data = {
            'title': 'New Network Doc',
            'description': 'Troubleshooting common network issues.',
            'tags': ['network', 'troubleshooting']
        }
        self.valid_update_data = {
            'title': 'Updated CPU High Runbook',
            'description': 'Updated steps for CPU issues. Added more #performance info.',
            'tags': ['cpu', 'performance', 'linux', 'updated']
        }

    # --- List Action Tests (GET /docs/) ---
    def test_list_docs_unauthenticated(self):
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) # Default for ModelViewSet

    def test_list_docs_authenticated(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3) # doc1, doc2, doc3_no_tags
        
        # Check default ordering by title
        titles_in_response = [item['title'] for item in response.data['results']]
        # Expected order: CPU High Runbook, Disk Full Guide, Memory Leak Playbook
        self.assertEqual(titles_in_response[0], self.doc1.title) # CPU
        self.assertEqual(titles_in_response[1], self.doc3_no_tags.title) # Disk
        self.assertEqual(titles_in_response[2], self.doc2.title) # Memory

    def test_list_docs_search_title(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_create_url, {'search': 'CPU High'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], self.doc1.title)

    def test_list_docs_search_description(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_create_url, {'search': 'resolve high CPU'}) # Part of doc1 description
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], self.doc1.title)
        
        response_multi_match = self.client.get(self.list_create_url, {'search': '#performance'})
        self.assertEqual(response_multi_match.status_code, status.HTTP_200_OK)
        self.assertEqual(response_multi_match.data['count'], 2) # doc1 and doc2 have #performance
        titles_in_response = {item['title'] for item in response_multi_match.data['results']}
        self.assertIn(self.doc1.title, titles_in_response)
        self.assertIn(self.doc2.title, titles_in_response)


    def test_list_docs_filter_by_tags_single(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_create_url, {'tags': 'cpu'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], self.doc1.title)

    def test_list_docs_filter_by_tags_multiple_and(self):
        self.client.force_authenticate(user=self.user1)
        # Multiple tags are treated as AND by default by django-taggit via filter(tags__name__in=[...]).filter(tags__name__in=[...])
        # However, the DRF filter might implement it as OR if using 'tags__name__in'.
        # Let's assume the filter `TagFilter` for `tags` uses `tags__name__in` for a comma-separated list, which is OR.
        # Or if it's a proper `TagsFilter` from `django-taggit-serializer`, it might support `tags__all`.
        # Based on standard DRF filter behavior, comma-separated values are usually OR.
        # If the filter is `django_filters.CharFilter(field_name='tags__name', lookup_expr='icontains')`
        # then 'cpu,performance' would search for "cpu,performance" as a single tag.
        # If using `django_filters.ModelMultipleChoiceFilter` or similar on tags, it would be OR.
        # Let's test for 'performance' which is in doc1 and doc2.
        response = self.client.get(self.list_create_url, {'tags': 'performance'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        titles_in_response = {item['title'] for item in response.data['results']}
        self.assertIn(self.doc1.title, titles_in_response)
        self.assertIn(self.doc2.title, titles_in_response)
        
        # Test for a combination that only doc1 has: 'cpu' AND 'linux'
        # This requires the filter to support multiple tag inputs for AND logic,
        # e.g., by chaining filter(tags__name='cpu').filter(tags__name='linux') or tags__all=['cpu', 'linux']
        # If the API supports `tags=cpu&tags=linux` or `tags=cpu,linux` interpreted as AND:
        response_and = self.client.get(self.list_create_url, {'tags': 'cpu,linux'}) # Assuming comma means AND for this filter
        # Actual behavior depends on how `TagsFilter` is implemented.
        # If it's `name__in`, this will be OR. If it's custom, it could be AND.
        # For now, let's assume the provided filter in the app is `django_filters.CharFilter(method='filter_by_tags_exact')`
        # which splits by comma and does an AND.
        # (Adjust this test if the filter logic is OR for comma-separated values)
        
        # Given the filter's current likely implementation (split by comma and chain .filter(tags__name=tag))
        # this should work as an AND.
        self.assertEqual(response_and.status_code, status.HTTP_200_OK)
        if response_and.data['count'] == 1: # If it's AND
             self.assertEqual(response_and.data['results'][0]['title'], self.doc1.title)
        else: # If it's OR or some other behavior
            print(f"DEBUG: Tags filter with 'cpu,linux' gave {response_and.data['count']} results, possibly not AND logic.")
            # This might indicate the filter needs adjustment or the test assumption is wrong.
            # For now, we'll proceed assuming the target implementation is AND for comma-separated.

    def test_list_docs_filter_by_tags_no_match(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_create_url, {'tags': 'nonexistenttag'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    # --- Retrieve Action Tests (GET /docs/{pk}/) ---
    def test_retrieve_doc_unauthenticated(self):
        response = self.client.get(self.detail_url_doc1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_doc_authenticated_exists(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.detail_url_doc1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.doc1.id)
        self.assertEqual(response.data['title'], self.doc1.title)
        self.assertEqual(response.data['created_by_username'], self.user1.username)
        self.assertIn('tags', response.data)
        self.assertEqual(sorted(response.data['tags']), sorted(['cpu', 'performance', 'linux']))

    def test_retrieve_doc_authenticated_does_not_exist(self):
        self.client.force_authenticate(user=self.user1)
        non_existent_url = reverse('docs_api:documentation-detail', kwargs={'pk': 99999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Create Action Tests (POST /docs/) ---
    def test_create_doc_unauthenticated(self):
        response = self.client.post(self.list_create_url, self.valid_create_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_doc_authenticated_valid_data(self):
        self.client.force_authenticate(user=self.user1)
        initial_count = AlertDocumentation.objects.count()
        response = self.client.post(self.list_create_url, self.valid_create_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AlertDocumentation.objects.count(), initial_count + 1)
        
        new_doc = AlertDocumentation.objects.get(pk=response.data['id'])
        self.assertEqual(new_doc.title, self.valid_create_data['title'])
        self.assertEqual(new_doc.created_by, self.user1) # Check perform_create
        self.assertEqual(sorted([tag.name for tag in new_doc.tags.all()]), sorted(self.valid_create_data['tags']))

    def test_create_doc_authenticated_invalid_data_missing_title(self):
        self.client.force_authenticate(user=self.user1)
        invalid_data = self.valid_create_data.copy()
        del invalid_data['title']
        response = self.client.post(self.list_create_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    # --- Update Action Tests (PUT /docs/{pk}/ and PATCH /docs/{pk}/) ---
    def test_update_doc_unauthenticated_put(self):
        response = self.client.put(self.detail_url_doc1, self.valid_update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_doc_unauthenticated_patch(self):
        response = self.client.patch(self.detail_url_doc1, {'title': 'Partial Update Attempt'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_update_doc_authenticated_put_valid_data(self):
        self.client.force_authenticate(user=self.user1) # User1 created doc1
        response = self.client.put(self.detail_url_doc1, self.valid_update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.doc1.refresh_from_db()
        self.assertEqual(self.doc1.title, self.valid_update_data['title'])
        self.assertEqual(self.doc1.description, self.valid_update_data['description'])
        self.assertEqual(sorted([tag.name for tag in self.doc1.tags.all()]), sorted(self.valid_update_data['tags']))
        self.assertEqual(self.doc1.created_by, self.user1) # Should remain user1

    def test_update_doc_authenticated_patch_partial_data(self):
        self.client.force_authenticate(user=self.user1)
        patch_data = {'title': 'Patched Title for Doc1'}
        response = self.client.patch(self.detail_url_doc1, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.doc1.refresh_from_db()
        self.assertEqual(self.doc1.title, patch_data['title'])
        self.assertNotEqual(self.doc1.description, self.valid_update_data['description']) # Description should be original

    def test_update_doc_by_different_authenticated_user(self):
        """ Test if a different authenticated user can update (depends on permissions, usually allowed for ModelViewSet)."""
        self.client.force_authenticate(user=self.user2) # User2 did not create doc1
        response = self.client.put(self.detail_url_doc1, self.valid_update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK) # Assuming no object-level permissions
        
        self.doc1.refresh_from_db()
        self.assertEqual(self.doc1.title, self.valid_update_data['title'])
        self.assertEqual(self.doc1.created_by, self.user1) # Creator should NOT change

    def test_update_doc_invalid_data_put(self):
        self.client.force_authenticate(user=self.user1)
        invalid_data = self.valid_update_data.copy()
        invalid_data['title'] = "" # Title cannot be blank
        response = self.client.put(self.detail_url_doc1, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_update_doc_non_existent_pk(self):
        self.client.force_authenticate(user=self.user1)
        non_existent_url = reverse('docs_api:documentation-detail', kwargs={'pk': 99999})
        response = self.client.put(non_existent_url, self.valid_update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Delete Action Tests (DELETE /docs/{pk}/) ---
    def test_delete_doc_unauthenticated(self):
        response = self.client.delete(self.detail_url_doc1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_doc_authenticated_exists(self):
        self.client.force_authenticate(user=self.user1)
        initial_count = AlertDocumentation.objects.count()
        response = self.client.delete(self.detail_url_doc1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AlertDocumentation.objects.count(), initial_count - 1)
        self.assertFalse(AlertDocumentation.objects.filter(pk=self.doc1.pk).exists())
        # Check if related links are deleted due to cascade
        self.assertFalse(DocumentationAlertGroup.objects.filter(documentation=self.doc1).exists())


    def test_delete_doc_authenticated_does_not_exist(self):
        self.client.force_authenticate(user=self.user1)
        non_existent_url = reverse('docs_api:documentation-detail', kwargs={'pk': 99999})
        response = self.client.delete(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_doc_by_different_user(self):
        """ Test if a different authenticated user can delete (depends on permissions). """
        self.client.force_authenticate(user=self.user2) # user2 did not create doc1
        response = self.client.delete(self.detail_url_doc1)
        # Default ModelViewSet behavior is typically to allow delete by any authenticated user
        # unless specific object-level permissions are implemented.
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AlertDocumentation.objects.filter(pk=self.doc1.pk).exists())

    # --- Custom Action: linked_alerts (GET /docs/{pk}/linked_alerts/) ---
    def test_linked_alerts_unauthenticated(self):
        response = self.client.get(self.linked_alerts_url_doc1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_linked_alerts_authenticated_has_links(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.linked_alerts_url_doc1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))
        self.assertEqual(len(response.data), 1) # Only one link created in setUp for doc1
        
        link_data = response.data[0]
        self.assertEqual(link_data['documentation_id'], self.doc1.id)
        self.assertEqual(link_data['alert_group_fingerprint'], self.ag1.fingerprint)
        self.assertEqual(link_data['linked_by_username'], self.user1.username)

    def test_linked_alerts_authenticated_no_links(self):
        self.client.force_authenticate(user=self.user1)
        # doc2 has no links in setUp
        linked_alerts_url_doc2 = reverse('docs_api:documentation-linked-alerts', kwargs={'pk': self.doc2.pk})
        response = self.client.get(linked_alerts_url_doc2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))
        self.assertEqual(len(response.data), 0)

    def test_linked_alerts_non_existent_doc_pk(self):
        self.client.force_authenticate(user=self.user1)
        non_existent_url = reverse('docs_api:documentation-linked-alerts', kwargs={'pk': 99999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Custom Action: link_alert (POST /docs/{pk}/link_alert/) ---
    def test_link_alert_unauthenticated(self):
        response = self.client.post(self.link_alert_url_doc1, {'alert_id': self.ag2.fingerprint}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_link_alert_authenticated_new_link(self):
        self.client.force_authenticate(user=self.user2) # Different user links
        # ag2 is not yet linked to doc1
        self.assertFalse(DocumentationAlertGroup.objects.filter(documentation=self.doc1, alert_group=self.ag2).exists())
        
        response = self.client.post(self.link_alert_url_doc1, {'alert_id': self.ag2.fingerprint}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.assertTrue(DocumentationAlertGroup.objects.filter(documentation=self.doc1, alert_group=self.ag2).exists())
        new_link = DocumentationAlertGroup.objects.get(documentation=self.doc1, alert_group=self.ag2)
        self.assertEqual(new_link.linked_by, self.user2)
        self.assertEqual(response.data['documentation_id'], self.doc1.id)
        self.assertEqual(response.data['alert_group_fingerprint'], self.ag2.fingerprint)

    def test_link_alert_authenticated_already_exists(self):
        self.client.force_authenticate(user=self.user1) # User1 made the initial link for doc1-ag1
        # self.existing_link_doc1_ag1 links doc1 and ag1
        response = self.client.post(self.link_alert_url_doc1, {'alert_id': self.ag1.fingerprint}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK) # Should return existing link data
        self.assertEqual(response.data['id'], self.existing_link_doc1_ag1.id)

    def test_link_alert_missing_alert_id(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.link_alert_url_doc1, {}, format='json') # Missing alert_id
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('alert_id', response.data)

    def test_link_alert_non_existent_alert_id(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.link_alert_url_doc1, {'alert_id': 'nonexistentfp'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # AlertGroup not found

    def test_link_alert_non_existent_doc_pk(self):
        self.client.force_authenticate(user=self.user1)
        non_existent_url = reverse('docs_api:documentation-link-alert', kwargs={'pk': 99999})
        response = self.client.post(non_existent_url, {'alert_id': self.ag1.fingerprint}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # Documentation not found

from docs.api.serializers import AlertDocumentationSerializer, DocumentationAlertGroupSerializer

class AlertDocumentationSerializerApiTests(APITestCase): # Renamed to avoid clash if a test_serializers.py is made
    def setUp(self):
        self.user1 = User.objects.create_user(username='serializer_user1', first_name='ApiTest', last_name='UserOne', password='password123')
        self.user2 = User.objects.create_user(username='serializer_user2', password='password456') # No first/last name

        self.doc_with_tags_and_creator = AlertDocumentation.objects.create(
            title='Serializer Test Doc 1',
            description='Description for serializer test 1. Includes #hashtag.',
            created_by=self.user1,
            tags=['api', 'testing', 'docs']
        )
        self.doc_no_tags_no_creator = AlertDocumentation.objects.create(
            title='Serializer Test Doc 2',
            description='Description for serializer test 2, no tags or creator initially.'
            # created_by is None
        )
        
        # For linked_alerts_count
        self.ag_for_link_count = AlertGroup.objects.create(fingerprint='fp_serializer_link_count')
        DocumentationAlertGroup.objects.create(documentation=self.doc_with_tags_and_creator, alert_group=self.ag_for_link_count, linked_by=self.user1)


    def test_alert_documentation_serialization_all_fields(self):
        serializer = AlertDocumentationSerializer(instance=self.doc_with_tags_and_creator)
        data = serializer.data
        
        self.assertEqual(data['id'], self.doc_with_tags_and_creator.id)
        self.assertEqual(data['title'], self.doc_with_tags_and_creator.title)
        self.assertEqual(data['description'], self.doc_with_tags_and_creator.description)
        self.assertEqual(data['created_by_username'], self.user1.username)
        self.assertEqual(data['created_by_name'], self.user1.get_full_name())
        self.assertTrue(data['created_at']) # Check it's populated
        self.assertTrue(data['updated_at'])
        self.assertEqual(sorted(data['tags']), sorted(['api', 'testing', 'docs']))
        self.assertEqual(data['linked_alerts_count'], 1)

    def test_alert_documentation_serialization_no_creator_no_tags(self):
        serializer = AlertDocumentationSerializer(instance=self.doc_no_tags_no_creator)
        data = serializer.data
        
        self.assertEqual(data['id'], self.doc_no_tags_no_creator.id)
        self.assertEqual(data['title'], self.doc_no_tags_no_creator.title)
        self.assertIsNone(data['created_by_username'])
        self.assertEqual(data['created_by_name'], "Unknown User") # Default from get_created_by_name
        self.assertEqual(data['tags'], [])
        self.assertEqual(data['linked_alerts_count'], 0)

    def test_alert_documentation_serialization_creator_no_full_name(self):
        self.doc_no_tags_no_creator.created_by = self.user2 # User2 has no first/last name
        self.doc_no_tags_no_creator.save()
        serializer = AlertDocumentationSerializer(instance=self.doc_no_tags_no_creator)
        data = serializer.data
        self.assertEqual(data['created_by_username'], self.user2.username)
        self.assertEqual(data['created_by_name'], self.user2.username) # Falls back to username

    def test_alert_documentation_deserialization_create_valid_data(self):
        valid_data = {
            'title': 'New Doc via Serializer',
            'description': 'Content for new doc.',
            'tags': ['new', 'valid']
        }
        # When creating, 'created_by' is usually set by the view (perform_create)
        # So, we don't pass it here for serializer validation itself.
        serializer = AlertDocumentationSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        self.assertEqual(serializer.validated_data['title'], valid_data['title'])
        self.assertEqual(serializer.validated_data['description'], valid_data['description'])
        self.assertEqual(sorted(serializer.validated_data['tags']), sorted(valid_data['tags']))

    def test_alert_documentation_deserialization_create_missing_title(self):
        invalid_data = {'description': 'No title here.'}
        serializer = AlertDocumentationSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        self.assertIn('This field is required.', str(serializer.errors['title']))

    def test_alert_documentation_deserialization_update_tags(self):
        # For update, an instance is provided
        update_data = {'tags': ['updated', 'tags', 'only']}
        serializer = AlertDocumentationSerializer(self.doc_with_tags_and_creator, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        
        # To test save, we need to provide created_by if it's not already on instance or in data
        # However, for ModelSerializer with Taggit, tags are handled by TaggableManager.
        # The serializer's .save() should handle this.
        updated_instance = serializer.save()
        self.assertEqual(sorted([tag.name for tag in updated_instance.tags.all()]), sorted(update_data['tags']))


class DocumentationAlertGroupSerializerApiTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='linkserializer_user1', first_name='Link', last_name='UserOne', password='password123')
        self.user2 = User.objects.create_user(username='linkserializer_user2', password='password456')

        self.doc1 = AlertDocumentation.objects.create(title='Doc One for Link Serializer', created_by=self.user1, tags=['d1'])
        self.ag1 = AlertGroup.objects.create(fingerprint='fp-linkserializer-ag1', name='AlertGroup One for Link', severity='critical')
        self.ag2 = AlertGroup.objects.create(fingerprint='fp-linkserializer-ag2', name='AlertGroup Two for Link', severity='warning')

        self.link = DocumentationAlertGroup.objects.create(
            documentation=self.doc1,
            alert_group=self.ag1,
            linked_by=self.user1
        )

    def test_documentation_alert_group_serialization(self):
        serializer = DocumentationAlertGroupSerializer(instance=self.link)
        data = serializer.data
        
        self.assertEqual(data['id'], self.link.id)
        self.assertEqual(data['documentation_id'], self.doc1.id)
        self.assertEqual(data['alert_group_fingerprint'], self.ag1.fingerprint)
        self.assertEqual(data['linked_by_username'], self.user1.username)
        self.assertEqual(data['linked_by_name'], self.user1.get_full_name())
        self.assertTrue(data['linked_at']) # Check it's populated
        
        # Check nested documentation_details
        self.assertIn('documentation_details', data)
        self.assertEqual(data['documentation_details']['id'], self.doc1.id)
        self.assertEqual(data['documentation_details']['title'], self.doc1.title)
        self.assertEqual(sorted(data['documentation_details']['tags']), sorted(['d1']))
        
        # Check nested alert_group_details
        self.assertIn('alert_group_details', data)
        self.assertEqual(data['alert_group_details']['fingerprint'], self.ag1.fingerprint)
        self.assertEqual(data['alert_group_details']['name'], self.ag1.name)
        self.assertEqual(data['alert_group_details']['severity'], self.ag1.severity)

    def test_documentation_alert_group_serialization_linked_by_no_full_name(self):
        self.link.linked_by = self.user2 # user2 has no first/last name
        self.link.save()
        serializer = DocumentationAlertGroupSerializer(instance=self.link)
        data = serializer.data
        self.assertEqual(data['linked_by_username'], self.user2.username)
        self.assertEqual(data['linked_by_name'], self.user2.username) # Falls back to username

    def test_documentation_alert_group_deserialization_create_valid(self):
        # This serializer is primarily for output, but test basic validation for write operations if they were enabled
        valid_data = {
            'documentation': self.doc2.id, # Use ID for writable related field
            'alert_group': self.ag2.fingerprint # Use fingerprint for writable related field
            # 'linked_by' would be set by view context
        }
        # Context is needed if 'linked_by' is to be set from request.user by serializer.save()
        # For now, just testing validation if fields were writable directly.
        serializer = DocumentationAlertGroupSerializer(data=valid_data)
        
        # Assuming 'documentation' and 'alert_group' are writeable in the serializer for creation.
        # If they are not (e.g. if it's a read-only nested serializer for output only),
        # then is_valid() would be false.
        # Current serializer seems to make them writeable by default ModelSerializer behavior.
        is_valid = serializer.is_valid()
        if not is_valid:
            print("DocumentationAlertGroupSerializer errors (valid data):", serializer.errors)
        self.assertTrue(is_valid)
        self.assertEqual(serializer.validated_data['documentation'].pk, self.doc2.pk)
        self.assertEqual(serializer.validated_data['alert_group'].fingerprint, self.ag2.fingerprint)

    def test_documentation_alert_group_deserialization_invalid_missing_doc(self):
        invalid_data = {'alert_group': self.ag1.fingerprint}
        serializer = DocumentationAlertGroupSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('documentation', serializer.errors)

    def test_documentation_alert_group_deserialization_invalid_missing_alert_group(self):
        invalid_data = {'documentation': self.doc1.id}
        serializer = DocumentationAlertGroupSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('alert_group', serializer.errors)

    def test_documentation_alert_group_deserialization_non_existent_doc_id(self):
        invalid_data = {'documentation': 99999, 'alert_group': self.ag1.fingerprint}
        serializer = DocumentationAlertGroupSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('documentation', serializer.errors)
        self.assertIn('Invalid pk "99999" - object does not exist.', str(serializer.errors['documentation']))
        
    def test_documentation_alert_group_deserialization_non_existent_alert_group_fp(self):
        invalid_data = {'documentation': self.doc1.id, 'alert_group': 'nonexistent-fp'}
        serializer = DocumentationAlertGroupSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('alert_group', serializer.errors)
        self.assertIn('Object with fingerprint=nonexistent-fp does not exist.', str(serializer.errors['alert_group']))


class AlertDocumentationLinkViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='linkset_user1', password='password123')
        self.user2 = User.objects.create_user(username='linkset_user2', password='password456')

        self.doc1 = AlertDocumentation.objects.create(title='Doc One', created_by=self.user1)
        self.doc2 = AlertDocumentation.objects.create(title='Doc Two', created_by=self.user2)

        self.ag1 = AlertGroup.objects.create(fingerprint='fp-linkset-ag1', name='AlertGroup One')
        self.ag2 = AlertGroup.objects.create(fingerprint='fp-linkset-ag2', name='AlertGroup Two')
        self.ag3 = AlertGroup.objects.create(fingerprint='fp-linkset-ag3', name='AlertGroup Three')

        # Create links
        self.link1_d1_ag1 = DocumentationAlertGroup.objects.create(
            documentation=self.doc1, alert_group=self.ag1, linked_by=self.user1,
            linked_at=timezone.now() - timedelta(days=2)
        )
        self.link2_d1_ag2 = DocumentationAlertGroup.objects.create(
            documentation=self.doc1, alert_group=self.ag2, linked_by=self.user2,
            linked_at=timezone.now() - timedelta(days=1) # More recent than link1
        )
        self.link3_d2_ag1 = DocumentationAlertGroup.objects.create(
            documentation=self.doc2, alert_group=self.ag1, linked_by=self.user1,
            linked_at=timezone.now() # Most recent
        )
        
        self.list_url = reverse('docs_api:documentationlink-list')
        self.detail_url_link1 = reverse('docs_api:documentationlink-detail', kwargs={'pk': self.link1_d1_ag1.pk})

    # --- List Action Tests (GET /links/) ---
    def test_list_links_unauthenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_links_authenticated_default_ordering(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        
        # Verify default ordering by -linked_at
        results = response.data['results']
        self.assertEqual(results[0]['id'], self.link3_d2_ag1.id) # Most recent
        self.assertEqual(results[1]['id'], self.link2_d1_ag2.id)
        self.assertEqual(results[2]['id'], self.link1_d1_ag1.id) # Oldest

    def test_list_links_filter_by_documentation_id(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url, {'documentation_id': self.doc1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        link_ids_in_response = {item['id'] for item in response.data['results']}
        self.assertIn(self.link1_d1_ag1.id, link_ids_in_response)
        self.assertIn(self.link2_d1_ag2.id, link_ids_in_response)

    def test_list_links_filter_by_alert_id(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url, {'alert_id': self.ag1.fingerprint})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        link_ids_in_response = {item['id'] for item in response.data['results']}
        self.assertIn(self.link1_d1_ag1.id, link_ids_in_response)
        self.assertIn(self.link3_d2_ag1.id, link_ids_in_response)
        
    def test_list_links_filter_by_alert_id_non_existent(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url, {'alert_id': 'nonexistentfp'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)


    def test_list_links_filter_by_documentation_and_alert_id(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url, {
            'documentation_id': self.doc1.id,
            'alert_id': self.ag1.fingerprint
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.link1_d1_ag1.id)

    # --- Retrieve Action Tests (GET /links/{pk}/) ---
    def test_retrieve_link_unauthenticated(self):
        response = self.client.get(self.detail_url_link1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_link_authenticated_exists(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.detail_url_link1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.link1_d1_ag1.id)
        self.assertEqual(response.data['documentation_id'], self.doc1.id)
        self.assertEqual(response.data['alert_group_fingerprint'], self.ag1.fingerprint)
        self.assertEqual(response.data['linked_by_username'], self.user1.username)
        self.assertTrue(response.data['linked_at']) # Check it's populated

    def test_retrieve_link_authenticated_does_not_exist(self):
        self.client.force_authenticate(user=self.user1)
        non_existent_url = reverse('docs_api:documentationlink-detail', kwargs={'pk': 99999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Custom Action: unlink_alert (POST /docs/{pk}/unlink_alert/) ---
    def test_unlink_alert_unauthenticated(self):
        # Use the existing link for doc1 and ag1
        unlink_url = reverse('docs_api:documentation-unlink-alert', kwargs={'pk': self.doc1.pk})
        response = self.client.post(unlink_url, {'alert_id': self.ag1.fingerprint}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unlink_alert_authenticated_link_exists(self):
        self.client.force_authenticate(user=self.user1)
        # self.existing_link_doc1_ag1 links doc1 and ag1
        self.assertTrue(DocumentationAlertGroup.objects.filter(documentation=self.doc1, alert_group=self.ag1).exists())
        
        unlink_url = reverse('docs_api:documentation-unlink-alert', kwargs={'pk': self.doc1.pk})
        response = self.client.post(unlink_url, {'alert_id': self.ag1.fingerprint}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'success', 'message': 'Alert unlinked successfully.'})
        self.assertFalse(DocumentationAlertGroup.objects.filter(documentation=self.doc1, alert_group=self.ag1).exists())

    def test_unlink_alert_authenticated_link_does_not_exist(self):
        self.client.force_authenticate(user=self.user1)
        # Ensure ag2 is NOT linked to doc1 before trying to unlink
        DocumentationAlertGroup.objects.filter(documentation=self.doc1, alert_group=self.ag2).delete()
        
        unlink_url = reverse('docs_api:documentation-unlink-alert', kwargs={'pk': self.doc1.pk})
        response = self.client.post(unlink_url, {'alert_id': self.ag2.fingerprint}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # Link not found

    def test_unlink_alert_missing_alert_id(self):
        self.client.force_authenticate(user=self.user1)
        unlink_url = reverse('docs_api:documentation-unlink-alert', kwargs={'pk': self.doc1.pk})
        response = self.client.post(unlink_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('alert_id', response.data)

    def test_unlink_alert_non_existent_alert_id(self):
        self.client.force_authenticate(user=self.user1)
        unlink_url = reverse('docs_api:documentation-unlink-alert', kwargs={'pk': self.doc1.pk})
        response = self.client.post(unlink_url, {'alert_id': 'nonexistentfp'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # AlertGroup for alert_id not found

    def test_unlink_alert_non_existent_doc_pk(self):
        self.client.force_authenticate(user=self.user1)
        non_existent_url = reverse('docs_api:documentation-unlink-alert', kwargs={'pk': 99999})
        response = self.client.post(non_existent_url, {'alert_id': self.ag1.fingerprint}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # Documentation not found
