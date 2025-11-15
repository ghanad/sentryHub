from django.contrib.auth.models import User
from django.test import TestCase

from users.models import UserProfile


class UserProfileModelTests(TestCase):
    def test_str_and_defaults(self):
        user = User.objects.create_user(username='alice')
        profile = user.profile
        self.assertEqual(str(profile), "alice's profile")
        self.assertEqual(profile.date_format_preference, 'gregorian')
        self.assertEqual(profile.timezone, 'UTC')
