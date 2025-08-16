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
        PhoneBook.objects.create(name='alice', phone_number='1')
        resp = self.client.get(reverse('integrations:phonebook-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'alice')
        self.assertContains(resp, reverse('integrations:phonebook-create'))

    def test_create_view(self):
        resp = self.client.post(
            reverse('integrations:phonebook-create'),
            {
                'name': 'bob',
                'phone_number': '2',
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(PhoneBook.objects.filter(name='bob').exists())

    def test_update_view(self):
        entry = PhoneBook.objects.create(name='charlie', phone_number='3')
        resp = self.client.post(
            reverse('integrations:phonebook-update', args=[entry.id]),
            {
                'name': 'charles',
                'phone_number': '33',
            },
        )
        self.assertEqual(resp.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.name, 'charles')
        self.assertEqual(entry.phone_number, '33')

    def test_delete_view(self):
        entry = PhoneBook.objects.create(name='dave', phone_number='4')
        resp = self.client.post(reverse('integrations:phonebook-delete', args=[entry.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(PhoneBook.objects.filter(id=entry.id).exists())
