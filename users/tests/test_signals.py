from django.contrib.auth.models import User
from django.test import TestCase

from users.models import UserProfile


class UserProfileSignalTests(TestCase):
    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(username='bob', password='pwd')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_profile_recreated_if_missing(self):
        user = User.objects.create_user(username='carol', password='pwd')
        user.profile.delete()
        user.first_name = 'C'
        user.save()
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
