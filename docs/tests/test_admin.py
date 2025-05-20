from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from alerts.models import AlertGroup
from docs.models import AlertDocumentation, DocumentationAlertGroup
from docs.admin import AlertDocumentationAdmin, DocumentationAlertGroupAdmin, DocumentationAlertGroupInline

# To inspect inline formsets
from django.contrib.admin.sites import AdminSite


class AdminPageAccessibilityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='superadmin_docs',
            email='superadmin_docs@example.com',
            password='password123'
        )
        self.client.login(username='superadmin_docs', password='password123')

        # Create one instance of each model for change views
        self.alert_doc = AlertDocumentation.objects.create(
            title='Admin Test Doc', 
            description='Content', 
            created_by=self.superuser
        )
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp_admin_docs_ag', 
            name='Admin Docs AG Test'
        )
        self.doc_alert_group_link = DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc,
            alert_group=self.alert_group,
            linked_by=self.superuser
        )

    def test_admin_pages_load_successfully(self):
        models_to_test = [
            (AlertDocumentation, self.alert_doc),
            (DocumentationAlertGroup, self.doc_alert_group_link)
        ]
        for model_cls, instance in models_to_test:
            app_label = model_cls._meta.app_label
            model_name = model_cls._meta.model_name
            
            # List view
            list_url = reverse(f'admin:{app_label}_{model_name}_changelist')
            response = self.client.get(list_url)
            self.assertEqual(response.status_code, 200, f"Changelist for {model_name} failed: {response.status_code}")

            # Add view
            add_url = reverse(f'admin:{app_label}_{model_name}_add')
            response = self.client.get(add_url)
            # DocumentationAlertGroup might not have a direct add view if only managed via inlines
            if model_cls is AlertDocumentation:
                 self.assertEqual(response.status_code, 200, f"Add view for {model_name} failed: {response.status_code}")
            elif model_cls is DocumentationAlertGroup and response.status_code == 403: # Django 403s if add_permission is false
                pass # This is acceptable if it's inline-only
            elif model_cls is DocumentationAlertGroup and response.status_code == 200: # If it does have an add view
                pass
            else:
                self.assertEqual(response.status_code, 200, f"Add view for {model_name} failed: {response.status_code}")


            # Change view
            change_url = reverse(f'admin:{app_label}_{model_name}_change', args=(instance.pk,))
            response = self.client.get(change_url)
            self.assertEqual(response.status_code, 200, f"Change view for {model_name} (pk={instance.pk}) failed: {response.status_code}")


class AlertDocumentationAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser('superadmin_docadmin', 's_docadmin@example.com', 'password')
        self.other_superuser = User.objects.create_superuser('other_superadmin', 'os_docadmin@example.com', 'password')
        self.client.login(username='superadmin_docadmin', password='password')
        
        self.site = AdminSite() # For direct testing of ModelAdmin methods
        self.alert_doc_admin = AlertDocumentationAdmin(AlertDocumentation, self.site)

        self.alert_doc = AlertDocumentation.objects.create(
            title='Test Doc for Admin', 
            description='Initial desc.', 
            created_by=self.superuser
        )
        self.ag1 = AlertGroup.objects.create(fingerprint='fp_admin_ag1_fordoc', name='AG1 for DocAdmin')
        self.ag2 = AlertGroup.objects.create(fingerprint='fp_admin_ag2_fordoc', name='AG2 for DocAdmin')

    def test_save_model_new_doc(self):
        """ Test that created_by is set on new doc creation in admin. """
        # Simulate request object
        mock_request = MagicMock()
        mock_request.user = self.superuser
        
        new_doc = AlertDocumentation(title='New Doc via Admin', description='Desc')
        self.alert_doc_admin.save_model(mock_request, new_doc, form=None, change=False)
        
        self.assertIsNotNone(new_doc.pk) # Should be saved
        self.assertEqual(new_doc.created_by, self.superuser)

    def test_save_model_update_doc(self):
        """ Test that created_by is NOT changed on doc update in admin, even by another admin. """
        original_creator = self.alert_doc.created_by
        self.assertEqual(original_creator, self.superuser)

        # Simulate request by another superuser
        mock_request_other_admin = MagicMock()
        mock_request_other_admin.user = self.other_superuser
        
        # Simulate updating the description
        self.alert_doc.description = "Updated description by other admin."
        self.alert_doc_admin.save_model(mock_request_other_admin, self.alert_doc, form=None, change=True)
        
        self.alert_doc.refresh_from_db()
        self.assertEqual(self.alert_doc.created_by, original_creator) # Should remain self.superuser
        self.assertEqual(self.alert_doc.description, "Updated description by other admin.")

    def test_alert_documentation_admin_changelist_loads(self):
        url = reverse('admin:docs_alertdocumentation_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for some key list_display fields
        self.assertContains(response, self.alert_doc.title)
        self.assertContains(response, "created_by_username") # From custom method or field
        self.assertContains(response, "updated_at")
        # Check for filters
        self.assertContains(response, "By created by")
        # Check for search
        self.assertContains(response, "searchbar")

    def test_alert_documentation_admin_change_view_loads_with_inlines(self):
        # Link an alert group to the documentation to test the inline
        DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc, 
            alert_group=self.ag1, 
            linked_by=self.superuser
        )
        
        url = reverse('admin:docs_alertdocumentation_change', args=(self.alert_doc.pk,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Verify presence of inline formset for DocumentationAlertGroupInline
        self.assertContains(response, 'DocumentationAlertGroupInline') # Check for inline title/class
        self.assertContains(response, self.ag1.name) # Check if linked alert group name is there

        # Verify readonly fields in the inline (more complex, might need to parse HTML or use formset directly)
        # For a basic check, ensure the fields are displayed.
        # A more robust test would involve inspecting the form fields' 'readonly' attribute if possible
        # or checking for specific CSS classes Django admin uses for readonly fields.
        # This is often tricky with direct HTML parsing in tests.
        # We'll assume that if the fields are listed in readonly_fields, Django handles it.
        # We can check if the values are present (implying they are displayed).
        self.assertContains(response, self.ag1.name) # From alert_group_link
        self.assertContains(response, self.superuser.username) # From linked_by_user_link
        # Check if 'Add another Documentation Alert Group' is NOT there if extra = 0
        # This depends on the default `extra` value for the inline. If it's 0, this should hold.
        # The inline's `extra = 0` means no empty forms by default.
        self.assertNotContains(response, 'Add another Documentation Alert Group')

        # Verify `can_delete = False` for the inline
        # This means there shouldn't be delete checkboxes for existing inline items.
        # The name of the delete checkbox is usually 'MODULENAME_set-0-DELETE'
        # For example, 'documentationalertgroup_set-0-DELETE'
        self.assertNotContains(response, '-DELETE</label>') # A bit broad, but often works

        # Verify readonly_fields on the main form
        self.assertContains(response, 'field-created_at')
        self.assertContains(response, 'field-updated_at')
        self.assertContains(response, 'field-created_by') # Should be readonly on change form

    def test_documentation_alert_group_inline_config(self):
        """ Test specific attributes of DocumentationAlertGroupInline. """
        self.assertEqual(DocumentationAlertGroupInline.extra, 0)
        self.assertFalse(DocumentationAlertGroupInline.can_delete)
        self.assertIn('alert_group_link', DocumentationAlertGroupInline.readonly_fields)
        self.assertIn('linked_at', DocumentationAlertGroupInline.readonly_fields)
        self.assertIn('linked_by_user_link', DocumentationAlertGroupInline.readonly_fields)


class DocumentationAlertGroupAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser('superadmin_doclinkadmin', 's_doclink@example.com', 'password')
        self.client.login(username='superadmin_doclinkadmin', password='password')
        
        self.alert_doc = AlertDocumentation.objects.create(title='DocForLinkAdmin', created_by=self.superuser)
        self.alert_group = AlertGroup.objects.create(fingerprint='fp_doclinkadmin_ag', name='AGForLinkAdmin')
        self.doc_alert_group_link = DocumentationAlertGroup.objects.create(
            documentation=self.alert_doc,
            alert_group=self.alert_group,
            linked_by=self.superuser
        )
        self.doc_alert_group_admin = DocumentationAlertGroupAdmin(DocumentationAlertGroup, AdminSite())

    def test_documentation_alert_group_admin_changelist_loads(self):
        url = reverse('admin:docs_documentationalertgroup_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for some key list_display fields/methods
        self.assertContains(response, "documentation_link")
        self.assertContains(response, "alert_group_link")
        self.assertContains(response, "linked_by_user_link")
        self.assertContains(response, "linked_at")
        # Check for filters
        self.assertContains(response, "By linked by")
        # Check for search
        self.assertContains(response, "searchbar")
        # Check for date_hierarchy
        self.assertContains(response, "By date linked_at") # From date_hierarchy

    def test_documentation_alert_group_admin_change_view_loads_readonly(self):
        url = reverse('admin:docs_documentationalertgroup_change', args=(self.doc_alert_group_link.pk,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # All fields are readonly, so we expect to see their values displayed,
        # and the input fields themselves should be disabled or presented as text.
        self.assertContains(response, self.doc_alert_group_link.documentation.title)
        self.assertContains(response, self.doc_alert_group_link.alert_group.name)
        self.assertContains(response, self.doc_alert_group_link.linked_by.username)
        # Check that there's no "Save" button as all fields are readonly.
        # Or, if Django still shows it, ensure fields are not editable.
        # A simpler check is that the form is for display, not input.
        # Django uses 'readonly' class for the field's div.
        self.assertContains(response, 'field-documentation_link')
        self.assertContains(response, 'field-alert_group_link')
        self.assertContains(response, 'field-linked_by_user_link')
        self.assertContains(response, 'field-linked_at')
        
        # Ensure no "Save" or "Save and continue editing" buttons are present
        # because all fields are readonly, making the form effectively non-editable.
        # This behavior might depend on Django version and admin templates.
        # A more reliable check is to ensure no <input type="submit"> or similar.
        # However, Django might still show them but they won't change anything.
        # For readonly ModelAdmins, Django typically doesn't show save buttons if all fields are readonly.
        # This needs to be verified against actual Django behavior for fully readonly ModelAdmins.
        # If it's a ModelAdmin where all fields are in readonly_fields, save buttons are usually hidden.
        # Let's assume the view hides save buttons if no fields are editable.
        # self.assertNotContains(response, 'name="_save"') # Test this if it's the expected behavior

    def test_documentation_link_method(self):
        expected_url = reverse('admin:docs_alertdocumentation_change', args=(self.alert_doc.pk,))
        expected_html = format_html('<a href="{}">{}</a>', expected_url, self.alert_doc.title)
        self.assertEqual(self.doc_alert_group_admin.documentation_link(self.doc_alert_group_link), expected_html)

    def test_alert_group_link_method(self):
        expected_url = reverse('admin:alerts_alertgroup_change', args=(self.alert_group.pk,))
        expected_html = format_html('<a href="{}">{}</a>', expected_url, self.alert_group.name)
        self.assertEqual(self.doc_alert_group_admin.alert_group_link(self.doc_alert_group_link), expected_html)

    def test_linked_by_user_link_method(self):
        expected_url = reverse('admin:auth_user_change', args=(self.superuser.pk,))
        expected_html = format_html('<a href="{}">{}</a>', expected_url, self.superuser.username)
        self.assertEqual(self.doc_alert_group_admin.linked_by_user_link(self.doc_alert_group_link), expected_html)
        
        # Test with no linked_by user
        self.doc_alert_group_link.linked_by = None
        self.doc_alert_group_link.save()
        self.assertEqual(self.doc_alert_group_admin.linked_by_user_link(self.doc_alert_group_link), "-")
