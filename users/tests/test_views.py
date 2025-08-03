from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.urls import reverse

from users.models import UserProfile
from users.views import update_preferences


class UpdatePreferencesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user3', password='pwd')
        self.factory = RequestFactory()

    def test_valid_update(self):
        request = self.factory.post(
            reverse('users:update_preferences'),
            {'date_format_preference': 'jalali'},
        )
        request.user = self.user
        request.session = {}
        setattr(request, '_messages', FallbackStorage(request))
        response = update_preferences(request)
        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.date_format_preference, 'jalali')

    def test_invalid_update_keeps_default(self):
        request = self.factory.post(
            reverse('users:update_preferences'),
            {'date_format_preference': 'invalid'},
        )
        request.user = self.user
        request.session = {}
        setattr(request, '_messages', FallbackStorage(request))
        response = update_preferences(request)
        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.date_format_preference, 'gregorian')


class UserListViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='admin', password='pwd', is_staff=True)
        self.regular = User.objects.create_user(username='guest', password='pwd')

    def test_non_staff_redirected(self):
        self.client.force_login(self.regular, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_access_and_search(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        User.objects.create_user(username='searchme', email='search@example.com')
        response = self.client.get(reverse('users:user_list'), {'search': 'searchme'})
        self.assertEqual(response.status_code, 200)
        users = list(response.context['users'])
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'searchme')
        self.assertEqual(response.context['search_query'], 'searchme')
