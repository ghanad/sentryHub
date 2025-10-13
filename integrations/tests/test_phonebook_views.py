from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from integrations.models import PhoneBook


class PhoneBookViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')
        self.client.login(username='tester', password='pass')

    def test_list_view(self):
        PhoneBook.objects.create(name='alice', phone_number='09100000000', contact_type=PhoneBook.TYPE_INTERNAL)
        resp = self.client.get(reverse('integrations:phonebook-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'alice')
        self.assertContains(resp, reverse('integrations:phonebook-create'))

    def test_create_view(self):
        resp = self.client.post(
            reverse('integrations:phonebook-create'),
            {
                'name': 'bob',
                'phone_number': '09100000001',
                'contact_type': PhoneBook.TYPE_INTERNAL,
                'is_active': 'on',
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"?tab={PhoneBook.TYPE_INTERNAL}", resp['Location'])
        self.assertTrue(PhoneBook.objects.filter(name='bob').exists())

    def test_create_view_rejects_invalid_phone_number(self):
        resp = self.client.post(
            reverse('integrations:phonebook-create'),
            {
                'name': 'invalid',
                'phone_number': '0912345',
                'contact_type': PhoneBook.TYPE_INTERNAL,
                'is_active': 'on',
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(
            resp,
            'form',
            'phone_number',
            'Enter a valid Iranian mobile number in the format 09XXXXXXXXX.',
        )
        self.assertFalse(PhoneBook.objects.filter(name='invalid').exists())

    def test_update_view(self):
        entry = PhoneBook.objects.create(name='charlie', phone_number='09100000002', contact_type=PhoneBook.TYPE_INTERNAL)
        resp = self.client.post(
            reverse('integrations:phonebook-update', args=[entry.id]),
            {
                'name': 'charles',
                'phone_number': '09100000003',
                'contact_type': PhoneBook.TYPE_OMS,
                'is_active': 'on',
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"?tab={PhoneBook.TYPE_OMS}", resp['Location'])
        entry.refresh_from_db()
        self.assertEqual(entry.name, 'charles')
        self.assertEqual(entry.phone_number, '09100000003')
        self.assertTrue(entry.is_active)
        self.assertEqual(entry.contact_type, PhoneBook.TYPE_OMS)

    def test_update_view_can_deactivate_entry(self):
        entry = PhoneBook.objects.create(
            name='diana',
            phone_number='09100000004',
            contact_type=PhoneBook.TYPE_INTERNAL,
            is_active=True,
        )
        resp = self.client.post(
            reverse('integrations:phonebook-update', args=[entry.id]),
            {
                'name': 'diana',
                'phone_number': '09100000004',
                'contact_type': PhoneBook.TYPE_INTERNAL,
                # Checkbox omitted to simulate unchecked state
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"?tab={PhoneBook.TYPE_INTERNAL}", resp['Location'])
        entry.refresh_from_db()
        self.assertFalse(entry.is_active)

    def test_delete_view(self):
        entry = PhoneBook.objects.create(name='dave', phone_number='09100000005', contact_type=PhoneBook.TYPE_INTERNAL)
        resp = self.client.post(reverse('integrations:phonebook-delete', args=[entry.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"?tab={PhoneBook.TYPE_INTERNAL}", resp['Location'])
        self.assertFalse(PhoneBook.objects.filter(id=entry.id).exists())

    def test_tabs_filter_by_contact_type(self):
        PhoneBook.objects.create(name='internal-user', phone_number='09100000006', contact_type=PhoneBook.TYPE_INTERNAL)
        PhoneBook.objects.create(name='oms-customer', phone_number='09100000007', contact_type=PhoneBook.TYPE_OMS)

        resp_internal = self.client.get(reverse('integrations:phonebook-list'))
        self.assertContains(resp_internal, 'internal-user')
        self.assertNotContains(resp_internal, 'oms-customer')

        resp_oms = self.client.get(reverse('integrations:phonebook-list'), {'tab': PhoneBook.TYPE_OMS})
        self.assertContains(resp_oms, 'oms-customer')
        self.assertNotContains(resp_oms, 'internal-user')

    def test_invalid_tab_defaults_to_internal(self):
        PhoneBook.objects.create(name='internal-user', phone_number='09100000006', contact_type=PhoneBook.TYPE_INTERNAL)
        resp = self.client.get(reverse('integrations:phonebook-list'), {'tab': 'unknown'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'internal-user')
