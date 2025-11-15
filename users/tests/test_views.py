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
            {
                'date_format_preference': 'jalali',
                'timezone': 'Asia/Tehran'
            },
        )
        request.user = self.user
        request.session = {}
        setattr(request, '_messages', FallbackStorage(request))
        response = update_preferences(request)
        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.date_format_preference, 'jalali')
        self.assertEqual(profile.timezone, 'Asia/Tehran')

    def test_invalid_update_keeps_default(self):
        request = self.factory.post(
            reverse('users:update_preferences'),
            {
                'date_format_preference': 'invalid',
                'timezone': 'UTC'
            },
        )
        request.user = self.user
        request.session = {}
        setattr(request, '_messages', FallbackStorage(request))
        response = update_preferences(request)
        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.date_format_preference, 'gregorian')
        self.assertEqual(profile.timezone, 'UTC')

    def test_invalid_timezone_keeps_default(self):
        request = self.factory.post(
            reverse('users:update_preferences'),
            {
                'date_format_preference': 'gregorian',
                'timezone': 'Invalid/Zone'
            },
        )
        request.user = self.user
        request.session = {}
        setattr(request, '_messages', FallbackStorage(request))
        response = update_preferences(request)
        self.assertEqual(response.status_code, 302)
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.timezone, 'UTC')


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


class PreferencesViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='pref', password='pwd', is_staff=True)
        self.regular = User.objects.create_user(username='prefreg', password='pwd')

    def test_non_staff_redirected(self):
        self.client.force_login(self.regular, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:preferences'))
        self.assertEqual(response.status_code, 302)

    def test_staff_get_creates_profile_and_sets_context(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:preferences'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'], self.staff)
        self.assertTrue(UserProfile.objects.filter(user=self.staff).exists())
        self.assertIn('timezone_choices', response.context)


class UserProfileViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='profile', password='pwd', is_staff=True)
        self.regular = User.objects.create_user(username='profilereg', password='pwd')

    def test_non_staff_redirected(self):
        self.client.force_login(self.regular, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 302)

    def test_staff_get_returns_context_and_creates_profile(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'], self.staff)
        self.assertTrue(UserProfile.objects.filter(user=self.staff).exists())


class UserCreateViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('admin', password='pwd', is_staff=True)
        self.regular = User.objects.create_user('regular', password='pwd')

    def test_permission_denied_for_non_staff(self):
        self.client.force_login(self.regular, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:user_create'))
        self.assertEqual(response.status_code, 302)

    def test_staff_get(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:user_create'))
        self.assertEqual(response.status_code, 200)

    def test_staff_post_creates_user(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'pass12345',
            'password2': 'pass12345',
        }
        response = self.client.post(reverse('users:user_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_ajax_invalid_data_returns_json_error(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        data = {
            'username': '',
            'email': 'x@example.com',
            'password1': 'a',
            'password2': 'b',
            'is_staff': False,
            'department': '',
            'phone_number': '',
        }
        response = self.client.post(
            reverse('users:user_create'),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'error')


class UserUpdateViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('admin', password='pwd', is_staff=True)
        self.target = User.objects.create_user('target', password='pwd', email='t@example.com')
        self.regular = User.objects.create_user('regular', password='pwd')

    def test_permission_denied_for_non_staff(self):
        self.client.force_login(self.regular, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:user_update', args=[self.target.pk]))
        self.assertEqual(response.status_code, 302)

    def test_staff_get(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:user_update', args=[self.target.pk]))
        self.assertEqual(response.status_code, 200)

    def test_staff_post_updates_user(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        data = {
            'username': 'target',
            'email': 'new@example.com',
            'is_staff': False,
            'department': '',
            'phone_number': '',
            'password1': '',
            'password2': '',
        }
        response = self.client.post(reverse('users:user_update', args=[self.target.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.target.refresh_from_db()
        self.assertEqual(self.target.email, 'new@example.com')

    def test_ajax_invalid_data_returns_json_error(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        data = {
            'username': 'target',
            'email': 'bad@example.com',
            'password1': 'a',
            'password2': 'b',
            'is_staff': False,
            'department': '',
            'phone_number': '',
        }
        response = self.client.post(
            reverse('users:user_update', args=[self.target.pk]),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'error')


class UserDeleteViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('admin', password='pwd', is_staff=True)
        self.target = User.objects.create_user('target', password='pwd')
        self.regular = User.objects.create_user('regular', password='pwd')

    def test_permission_denied_for_non_staff(self):
        self.client.force_login(self.regular, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:user_delete', args=[self.target.pk]))
        self.assertEqual(response.status_code, 302)

    def test_staff_get(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('users:user_delete', args=[self.target.pk]))
        self.assertEqual(response.status_code, 200)

    def test_ajax_get_disallowed(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(
            reverse('users:user_delete', args=[self.target.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()['status'], 'error')

    def test_staff_post_deletes_user(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.post(reverse('users:user_delete', args=[self.target.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=self.target.pk).exists())

    def test_ajax_post_returns_success(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        another = User.objects.create_user('another', password='pwd')
        response = self.client.post(
            reverse('users:user_delete', args=[another.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertFalse(User.objects.filter(pk=another.pk).exists())
