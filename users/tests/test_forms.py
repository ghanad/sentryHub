from django.contrib.auth.models import User
from django.test import TestCase

from users.forms import CustomUserCreationForm, CustomUserChangeForm


class CustomUserCreationFormTests(TestCase):
    def test_save_creates_user_and_profile(self):
        form = CustomUserCreationForm(
            data={
                'username': 'dave',
                'email': 'dave@example.com',
                'password1': 'strong-pass123',
                'password2': 'strong-pass123',
                'is_staff': True,
                'department': 'IT',
                'phone_number': '123',
            }
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        user.refresh_from_db()
        self.assertEqual(user.email, 'dave@example.com')
        self.assertTrue(user.is_staff)
        profile = user.profile
        self.assertEqual(profile.department, 'IT')
        self.assertEqual(profile.phone_number, '123')

    def test_password_mismatch_is_invalid(self):
        form = CustomUserCreationForm(
            data={
                'username': 'dave',
                'email': 'dave@example.com',
                'password1': 'pass1',
                'password2': 'pass2',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)


class CustomUserChangeFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='erin', email='erin@example.com', password='oldpass'
        )
        profile = self.user.profile
        profile.department = 'Old'
        profile.phone_number = '000'
        profile.save()

    def test_save_updates_user_and_profile(self):
        form = CustomUserChangeForm(
            data={
                'username': 'erin',
                'email': 'new@example.com',
                'is_staff': True,
                'department': 'NewDept',
                'phone_number': '111',
                'password1': 'newpass123',
                'password2': 'newpass123',
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password('newpass123'))
        profile = user.profile
        self.assertEqual(profile.department, 'NewDept')
        self.assertEqual(profile.phone_number, '111')

    def test_mismatched_passwords_invalid(self):
        form = CustomUserChangeForm(
            data={
                'username': 'erin',
                'email': 'erin@example.com',
                'is_staff': False,
                'department': 'Dept',
                'phone_number': '222',
                'password1': 'one',
                'password2': 'two',
            },
            instance=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
