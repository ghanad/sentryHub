from django.test import TestCase
from django.contrib.auth.models import User
from django.db.utils import IntegrityError, DataError
from django.db.models.signals import post_save 
from django.core.exceptions import ValidationError


from users.models import UserProfile
# Import signals to disconnect them for specific tests if necessary
from users.signals import create_user_profile, save_user_profile 

class UserProfileModelTests(TestCase):
    def setUp(self):
        # Disconnect signals to test UserProfile model in isolation for some tests
        post_save.disconnect(create_user_profile, sender=User)
        post_save.disconnect(save_user_profile, sender=User)
        
        self.user = User.objects.create_user(
            username='testuser_profile', 
            email='test_profile@example.com', 
            password='password123'
        )

    def tearDown(self):
        # Reconnect signals after tests
        post_save.connect(create_user_profile, sender=User)
        post_save.connect(save_user_profile, sender=User)

    def test_user_profile_manual_creation_and_defaults(self):
        """ Test UserProfile manual creation and its default values. """
        profile = UserProfile.objects.create(user=self.user)
        self.assertIsNotNone(profile.pk)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.date_format_preference, 'gregorian') # Default value
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)
        self.assertTrue(profile.created_at <= profile.updated_at)

    def test_user_profile_str_method(self):
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(str(profile), f"{self.user.username}'s profile")

    def test_user_profile_cascade_delete_on_user_delete(self):
        # Re-enable signals for this test to ensure profile exists, or create manually
        post_save.connect(create_user_profile, sender=User)
        post_save.connect(save_user_profile, sender=User)
        
        user_to_delete = User.objects.create_user(username='user_to_delete', password='password')
        # Profile should be created by signal now
        try:
            profile = UserProfile.objects.get(user=user_to_delete)
        except UserProfile.DoesNotExist:
            self.fail("UserProfile was not created for user_to_delete, even with signals reconnected.")
            
        profile_pk = profile.pk
        
        self.assertTrue(UserProfile.objects.filter(pk=profile_pk).exists())
        user_to_delete.delete()
        self.assertFalse(UserProfile.objects.filter(pk=profile_pk).exists())

        # Disconnect again if other tests in this class need isolation
        post_save.disconnect(create_user_profile, sender=User)
        post_save.disconnect(save_user_profile, sender=User)


    def test_user_profile_date_format_preference_choices_valid(self):
        profile = UserProfile.objects.create(user=self.user)
        profile.date_format_preference = 'jalali'
        profile.full_clean() # Should not raise ValidationError
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.date_format_preference, 'jalali')

        profile.date_format_preference = 'gregorian'
        profile.full_clean() # Should not raise ValidationError
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.date_format_preference, 'gregorian')


    def test_user_profile_date_format_preference_choices_invalid(self):
        profile = UserProfile.objects.create(user=self.user)
        profile.date_format_preference = 'invalid_choice'
        with self.assertRaises(ValidationError) as context:
            profile.full_clean() 
        
        self.assertIn('date_format_preference', context.exception.message_dict)
        self.assertIn("'invalid_choice' is not a valid choice.", str(context.exception.message_dict['date_format_preference']))
        
        # Test database constraint if field was an ENUM (CharField doesn't enforce this at DB level by default)
        # For CharField with choices, Django's validation layer (like full_clean or ModelForm) enforces it.
        # Direct save without full_clean might succeed if the string length is okay.
        # To be robust, ensure full_clean is called or rely on form validation.

class UserSignalTests(TestCase):
    def setUp(self):
        # Signals are connected by default as per apps.py
        self.user_data = {
            'username': 'signaltestuser',
            'email': 'signal@example.com',
            'password': 'password123'
        }
        self.user_data2 = {
            'username': 'signaltestuser2',
            'email': 'signal2@example.com',
            'password': 'password123'
        }

    def test_create_user_profile_signal_on_new_user(self):
        """ Test that create_user_profile signal creates a profile for a new user. """
        self.assertEqual(UserProfile.objects.count(), 0)
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(UserProfile.objects.count(), 1)
        
        try:
            profile = UserProfile.objects.get(user=user)
            self.assertIsNotNone(profile)
            self.assertEqual(profile.user, user)
            self.assertEqual(profile.date_format_preference, 'gregorian') # Check default
        except UserProfile.DoesNotExist:
            self.fail("UserProfile was not created by signal for new user.")

    def test_save_user_profile_signal_on_existing_user_no_profile(self):
        """ Test save_user_profile creates profile if user exists but profile doesn't. """
        # Temporarily disconnect create_user_profile to simulate user existing without profile
        post_save.disconnect(create_user_profile, sender=User)
        user_no_profile = User.objects.create_user(**self.user_data)
        post_save.connect(create_user_profile, sender=User) # Reconnect

        self.assertFalse(UserProfile.objects.filter(user=user_no_profile).exists())
        
        # Now save the user again, which should trigger save_user_profile
        user_no_profile.email = 'new_email@example.com' # Make a change to ensure save does something
        user_no_profile.save()

        self.assertTrue(UserProfile.objects.filter(user=user_no_profile).exists())
        profile = UserProfile.objects.get(user=user_no_profile)
        self.assertEqual(profile.date_format_preference, 'gregorian')

    def test_save_user_profile_signal_on_existing_user_with_profile(self):
        """ Test save_user_profile doesn't create new profile if one exists. """
        user = User.objects.create_user(**self.user_data) # Profile created by create_user_profile
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)


class UserProfileViewTests(UserViewTestBase): # Inherit from UserViewTestBase for user setup
    def setUp(self):
        super().setUp() # Call parent setUp to have self.regular_user, self.staff_user, self.login_url
        self.profile_url = reverse('users:profile')
        # Ensure the regular_user for these tests does not have a profile initially to test creation
        UserProfile.objects.filter(user=self.regular_user).delete()
        self.assertFalse(UserProfile.objects.filter(user=self.regular_user).exists())


    def test_user_profile_view_unauthenticated(self):
        response = self.client.get(self.profile_url)
        expected_redirect_url = f"{self.login_url}?next={self.profile_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)

    def test_user_profile_view_authenticated_get_profile_creation(self):
        self.client.login(username=self.regular_user.username, password='password123')
        self.assertFalse(UserProfile.objects.filter(user=self.regular_user).exists()) # Pre-condition
        
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile.html')
        
        self.assertTrue(UserProfile.objects.filter(user=self.regular_user).exists()) # Profile created
        profile = UserProfile.objects.get(user=self.regular_user)
        
        self.assertEqual(response.context['user'], self.regular_user)
        self.assertEqual(response.context['profile'], profile)
        self.assertEqual(profile.date_format_preference, 'gregorian') # Default

    def test_user_profile_view_authenticated_get_profile_exists(self):
        # Ensure profile exists for this test (e.g., for staff user whose profile was created in base setUp)
        self.client.login(username=self.staff_user.username, password='password123')
        self.assertTrue(UserProfile.objects.filter(user=self.staff_user).exists()) # Pre-condition from base
        
        response = self.client.get(self.profile_url) # Staff user accesses their own profile
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile.html')
        
        self.assertEqual(response.context['user'], self.staff_user)
        self.assertEqual(response.context['profile'], self.staff_user_profile)
        # Check existing preference if different from default
        self.staff_user_profile.date_format_preference = 'jalali'
        self.staff_user_profile.save()
        
        response_after_change = self.client.get(self.profile_url)
        self.assertEqual(response_after_change.context['profile'].date_format_preference, 'jalali')


class PreferencesViewTests(UserViewTestBase):
    def setUp(self):
        super().setUp()
        self.preferences_url = reverse('users:preferences')
        # Ensure regular_user does not have a profile initially for one of the tests
        UserProfile.objects.filter(user=self.regular_user).delete()

    def test_preferences_view_unauthenticated(self):
        response = self.client.get(self.preferences_url)
        expected_redirect_url = f"{self.login_url}?next={self.preferences_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)

    def test_preferences_view_authenticated_get_profile_creation(self):
        self.client.login(username=self.regular_user.username, password='password123')
        self.assertFalse(UserProfile.objects.filter(user=self.regular_user).exists()) # Pre-condition
        
        response = self.client.get(self.preferences_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/preferences.html')
        
        self.assertTrue(UserProfile.objects.filter(user=self.regular_user).exists()) # Profile created
        profile = UserProfile.objects.get(user=self.regular_user)
        
        self.assertEqual(response.context['user'], self.regular_user)
        self.assertEqual(response.context['profile'], profile)
        self.assertEqual(profile.date_format_preference, 'gregorian')

    def test_preferences_view_authenticated_get_profile_exists(self):
        self.client.login(username=self.staff_user.username, password='password123')
        self.assertTrue(UserProfile.objects.filter(user=self.staff_user).exists()) # Pre-condition
        
        self.staff_user_profile.date_format_preference = 'jalali'
        self.staff_user_profile.save()

        response = self.client.get(self.preferences_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/preferences.html')
        
        self.assertEqual(response.context['user'], self.staff_user)
        self.assertEqual(response.context['profile'], self.staff_user_profile)
        self.assertEqual(response.context['profile'].date_format_preference, 'jalali')


class UpdatePreferencesViewTests(UserViewTestBase):
    def setUp(self):
        super().setUp()
        self.update_preferences_url = reverse('users:update_preferences')
        self.preferences_url = reverse('users:preferences') # For redirect checks
        # Ensure regular_user does not have a profile initially for one of the tests
        UserProfile.objects.filter(user=self.regular_user).delete()

    def test_update_preferences_unauthenticated(self):
        response = self.client.post(self.update_preferences_url, {'date_format_preference': 'jalali'})
        expected_redirect_url = f"{self.login_url}?next={self.update_preferences_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)

    def test_update_preferences_get_not_allowed(self):
        self.client.login(username=self.regular_user.username, password='password123')
        response = self.client.get(self.update_preferences_url)
        # The view redirects to 'users:preferences' for GET requests (as per current view logic)
        self.assertRedirects(response, self.preferences_url, fetch_redirect_response=False)

    @patch('django.contrib.messages.success')
    def test_update_preferences_post_valid_jalali_profile_exists(self, mock_messages_success):
        self.client.login(username=self.staff_user.username, password='password123') # staff_user has profile
        self.assertEqual(self.staff_user_profile.date_format_preference, 'gregorian') # Initial default
        
        response = self.client.post(self.update_preferences_url, {'date_format_preference': 'jalali'})
        
        self.assertRedirects(response, self.preferences_url)
        self.staff_user_profile.refresh_from_db()
        self.assertEqual(self.staff_user_profile.date_format_preference, 'jalali')
        mock_messages_success.assert_called_once_with(
            response.wsgi_request, # Access request from response after redirect
            'Preferences updated successfully.'
        )

    @patch('django.contrib.messages.success')
    def test_update_preferences_post_valid_gregorian_profile_creation(self, mock_messages_success):
        self.client.login(username=self.regular_user.username, password='password123')
        self.assertFalse(UserProfile.objects.filter(user=self.regular_user).exists()) # No profile initially

        response = self.client.post(self.update_preferences_url, {'date_format_preference': 'gregorian'})
        
        self.assertRedirects(response, self.preferences_url)
        self.assertTrue(UserProfile.objects.filter(user=self.regular_user).exists())
        profile = UserProfile.objects.get(user=self.regular_user)
        self.assertEqual(profile.date_format_preference, 'gregorian')
        mock_messages_success.assert_called_once()

    @patch('django.contrib.messages.error')
    def test_update_preferences_post_invalid_preference_value(self, mock_messages_error):
        self.client.login(username=self.staff_user.username, password='password123')
        initial_preference = self.staff_user_profile.date_format_preference
        
        response = self.client.post(self.update_preferences_url, {'date_format_preference': 'invalid_value'})
        
        self.assertRedirects(response, self.preferences_url)
        self.staff_user_profile.refresh_from_db()
        self.assertEqual(self.staff_user_profile.date_format_preference, initial_preference) # Should not change
        mock_messages_error.assert_called_once_with(
            response.wsgi_request,
            'Invalid preference selected.'
        )

    @patch('django.contrib.messages.error')
    def test_update_preferences_post_missing_preference_field(self, mock_messages_error):
        self.client.login(username=self.staff_user.username, password='password123')
        initial_preference = self.staff_user_profile.date_format_preference
        
        response = self.client.post(self.update_preferences_url, {}) # Missing field
        
        self.assertRedirects(response, self.preferences_url)
        self.staff_user_profile.refresh_from_db()
        self.assertEqual(self.staff_user_profile.date_format_preference, initial_preference)
        mock_messages_error.assert_called_once_with(
            response.wsgi_request,
            'Invalid preference selected.' # Current view logic lumps missing and invalid together
        )

from django import forms as django_forms
from users.forms import CustomUserCreationForm, CustomUserChangeForm


class CustomUserCreationFormTests(TestCase):
    def setUp(self):
        self.valid_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'ValidP@ss1',
            'password2': 'ValidP@ss1',
            'department': 'Engineering',
            'phone_number': '123-456-7890',
            'is_staff': True
        }
        self.user_already_exists = User.objects.create_user(username='existinguser', password='password')

    def test_custom_user_creation_form_valid_data(self):
        form = CustomUserCreationForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")
        
        user = form.save()
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.username, self.valid_data['username'])
        self.assertEqual(user.email, self.valid_data['email'])
        self.assertTrue(user.check_password(self.valid_data['password1']))
        self.assertEqual(user.is_staff, self.valid_data['is_staff'])
        
        # Check UserProfile
        self.assertTrue(hasattr(user, 'userprofile'))
        self.assertEqual(user.userprofile.department, self.valid_data['department'])
        self.assertEqual(user.userprofile.phone_number, self.valid_data['phone_number'])

    def test_custom_user_creation_form_valid_data_optional_fields_blank(self):
        data = self.valid_data.copy()
        data['department'] = ''
        data['phone_number'] = ''
        data['is_staff'] = False # Test default if not provided, or explicit False
        
        form = CustomUserCreationForm(data=data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")
        user = form.save()
        self.assertEqual(user.userprofile.department, '')
        self.assertEqual(user.userprofile.phone_number, '')
        self.assertFalse(user.is_staff)

    def test_custom_user_creation_form_invalid_data(self):
        # Missing username
        data = self.valid_data.copy(); del data['username']
        form = CustomUserCreationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

        # Missing email
        data = self.valid_data.copy(); del data['email']
        form = CustomUserCreationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

        # Missing password1
        data = self.valid_data.copy(); del data['password1']
        form = CustomUserCreationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

        # Missing password2
        data = self.valid_data.copy(); del data['password2']
        form = CustomUserCreationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

        # Passwords mismatch
        data = self.valid_data.copy(); data['password2'] = 'WrongP@ss1'
        form = CustomUserCreationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors) # Django's UserCreationForm adds error to password2
        self.assertIn("The two password fields didn’t match.", form.errors['password2'])


        # Invalid email
        data = self.valid_data.copy(); data['email'] = 'not-an-email'
        form = CustomUserCreationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

        # Username already exists
        data = self.valid_data.copy(); data['username'] = 'existinguser'
        form = CustomUserCreationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn("A user with that username already exists.", form.errors['username'])

    def test_custom_user_creation_form_widget_configuration(self):
        form = CustomUserCreationForm()
        self.assertIsInstance(form.fields['username'].widget, django_forms.TextInput)
        self.assertEqual(form.fields['username'].widget.attrs.get('class'), 'form-control')
        
        self.assertIsInstance(form.fields['email'].widget, django_forms.EmailInput)
        self.assertEqual(form.fields['email'].widget.attrs.get('class'), 'form-control')

        self.assertIsInstance(form.fields['password1'].widget, django_forms.PasswordInput)
        self.assertEqual(form.fields['password1'].widget.attrs.get('class'), 'form-control')
        
        self.assertIsInstance(form.fields['password2'].widget, django_forms.PasswordInput)
        self.assertEqual(form.fields['password2'].widget.attrs.get('class'), 'form-control')

        self.assertIsInstance(form.fields['department'].widget, django_forms.TextInput)
        self.assertEqual(form.fields['department'].widget.attrs.get('class'), 'form-control')

        self.assertIsInstance(form.fields['phone_number'].widget, django_forms.TextInput)
        self.assertEqual(form.fields['phone_number'].widget.attrs.get('class'), 'form-control')

        self.assertIsInstance(form.fields['is_staff'].widget, django_forms.CheckboxInput)
        self.assertEqual(form.fields['is_staff'].widget.attrs.get('class'), 'form-check-input')


class CustomUserChangeFormTests(TestCase):
    def setUp(self):
        self.user_with_profile = User.objects.create_user(
            username='changeuser', email='change@example.com', password='password123'
        )
        # Profile automatically created by signal
        self.profile = self.user_with_profile.userprofile
        self.profile.department = 'Initial Department'
        self.profile.phone_number = '000-000-0000'
        self.profile.save()

        self.user_no_profile_yet = User.objects.create_user(
            username='changenoprofile', email='changenp@example.com', password='password123'
        )
        # Manually delete profile if signals auto-created it, to test init scenario
        UserProfile.objects.filter(user=self.user_no_profile_yet).delete()


        self.valid_change_data = {
            'username': 'changeuser', # Usually readonly or handled by admin, but form includes it
            'email': 'changed_email@example.com',
            'department': 'Updated Department',
            'phone_number': '111-222-3333',
            'is_staff': True,
            'password': '', # For password change tests
            'password_confirm': ''
        }

    def test_custom_user_change_form_initialization_with_profile(self):
        form = CustomUserChangeForm(instance=self.user_with_profile)
        self.assertEqual(form.initial.get('department'), self.profile.department)
        self.assertEqual(form.initial.get('phone_number'), self.profile.phone_number)
        self.assertEqual(form.initial.get('email'), self.user_with_profile.email)

    def test_custom_user_change_form_initialization_no_profile(self):
        # Ensure no profile exists
        self.assertFalse(UserProfile.objects.filter(user=self.user_no_profile_yet).exists())
        form = CustomUserChangeForm(instance=self.user_no_profile_yet)
        self.assertEqual(form.initial.get('department'), '')
        self.assertEqual(form.initial.get('phone_number'), '')
        self.assertEqual(form.initial.get('email'), self.user_no_profile_yet.email)
        # Saving this form should create a profile
        form_data = {
            'username': self.user_no_profile_yet.username,
            'email': 'newemail@example.com',
            'department': 'Newly Added Dept',
            'phone_number': '555-555-5555',
            'is_staff': False,
            'password': '', 'password_confirm': ''
        }
        form_to_save = CustomUserChangeForm(data=form_data, instance=self.user_no_profile_yet)
        self.assertTrue(form_to_save.is_valid(), msg=form_to_save.errors)
        saved_user = form_to_save.save()
        self.assertTrue(UserProfile.objects.filter(user=saved_user).exists())
        self.assertEqual(saved_user.userprofile.department, 'Newly Added Dept')


    def test_custom_user_change_form_valid_data_no_password_change(self):
        form = CustomUserChangeForm(data=self.valid_change_data, instance=self.user_with_profile)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")
        
        original_password_hash = self.user_with_profile.password
        user = form.save()
        user.refresh_from_db() # Ensure we get the latest from DB
        
        self.assertEqual(user.email, self.valid_change_data['email'])
        self.assertEqual(user.is_staff, self.valid_change_data['is_staff'])
        self.assertTrue(hasattr(user, 'userprofile'))
        self.assertEqual(user.userprofile.department, self.valid_change_data['department'])
        self.assertEqual(user.userprofile.phone_number, self.valid_change_data['phone_number'])
        self.assertEqual(user.password, original_password_hash) # Password should not change

    def test_custom_user_change_form_valid_data_with_password_change(self):
        data = self.valid_change_data.copy()
        data['password'] = 'NewP@ssw0rd1'
        data['password_confirm'] = 'NewP@ssw0rd1'
        
        form = CustomUserChangeForm(data=data, instance=self.user_with_profile)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")
        
        user = form.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password(data['password']))

    def test_custom_user_change_form_invalid_data(self):
        # Mismatched passwords
        data = self.valid_change_data.copy()
        data['password'] = 'NewP@ssw0rd1'
        data['password_confirm'] = 'MistakeP@ss'
        form = CustomUserChangeForm(data=data, instance=self.user_with_profile)
        self.assertFalse(form.is_valid())
        self.assertIn('password_confirm', form.errors)
        self.assertIn("The two password fields didn’t match.", form.errors['password_confirm'])

        # Password1 provided, password2 blank
        data = self.valid_change_data.copy()
        data['password'] = 'NewP@ssw0rd1'
        data['password_confirm'] = '' # Blank
        form = CustomUserChangeForm(data=data, instance=self.user_with_profile)
        self.assertFalse(form.is_valid())
        self.assertIn('password_confirm', form.errors)
        self.assertIn("This field is required.", str(form.errors['password_confirm'])) # Or custom message

        # Invalid email
        data = self.valid_change_data.copy(); data['email'] = 'not-an-email'
        form = CustomUserChangeForm(data=data, instance=self.user_with_profile)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_custom_user_change_form_widget_and_help_text(self):
        form = CustomUserChangeForm(instance=self.user_with_profile)
        
        # Check widgets and classes
        self.assertIsInstance(form.fields['email'].widget, django_forms.EmailInput)
        self.assertEqual(form.fields['email'].widget.attrs.get('class'), 'form-control')
        
        self.assertIsInstance(form.fields['department'].widget, django_forms.TextInput)
        self.assertEqual(form.fields['department'].widget.attrs.get('class'), 'form-control')
        
        self.assertIsInstance(form.fields['phone_number'].widget, django_forms.TextInput)
        self.assertEqual(form.fields['phone_number'].widget.attrs.get('class'), 'form-control')
        
        self.assertIsInstance(form.fields['is_staff'].widget, django_forms.CheckboxInput)
        self.assertEqual(form.fields['is_staff'].widget.attrs.get('class'), 'form-check-input')

        self.assertIsInstance(form.fields['password'].widget, django_forms.PasswordInput)
        self.assertEqual(form.fields['password'].widget.attrs.get('class'), 'form-control')
        
        self.assertIsInstance(form.fields['password_confirm'].widget, django_forms.PasswordInput)
        self.assertEqual(form.fields['password_confirm'].widget.attrs.get('class'), 'form-control')

        # Check help texts for password fields
        self.assertIn("leave blank to keep the current password", form.fields['password'].help_text.lower())
        self.assertIn("confirm the new password", form.fields['password_confirm'].help_text.lower())

from django.urls import reverse
from django.conf import settings
from django.test import Client
from django.contrib.messages import get_messages
from unittest.mock import patch # Already imported for middleware tests, but good to have here too

# --- View Tests ---

class UserViewTestBase(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('users:login') # Assuming your login URL is namespaced
        
        self.staff_user = User.objects.create_user(
            username='staffuser_view', 
            password='password123', 
            email='staff_view@example.com',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regularuser_view', 
            password='password123', 
            email='regular_view@example.com',
            is_staff=False
        )
        # UserProfile for staff_user (created by signal)
        self.staff_user_profile = self.staff_user.userprofile
        self.staff_user_profile.department = "IT"
        self.staff_user_profile.save()

        # UserProfile for regular_user
        self.regular_user_profile = self.regular_user.userprofile
        self.regular_user_profile.department = "Sales"
        self.regular_user_profile.save()
        
        self.user_list_url = reverse('users:user-list')
        self.user_create_url = reverse('users:user-create')
        self.user_update_url = reverse('users:user-update', kwargs={'pk': self.regular_user.pk})
        self.user_delete_url = reverse('users:user-delete', kwargs={'pk': self.regular_user.pk})


class UserListViewTests(UserViewTestBase):
    def test_user_list_view_unauthenticated(self):
        response = self.client.get(self.user_list_url)
        expected_redirect_url = f"{self.login_url}?next={self.user_list_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)

    def test_user_list_view_authenticated_non_staff(self):
        self.client.login(username=self.regular_user.username, password='password123')
        response = self.client.get(self.user_list_url)
        # AdminRequiredMixin redirects to login with a message
        expected_redirect_url = f"{self.login_url}?next={self.user_list_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)
        
        # Check for the message (requires messages middleware to be active and storage configured)
        # For direct client testing, need to get messages from the response after redirect is followed, or from session
        # This is easier if testing the middleware itself, or by inspecting session if test client stores it.
        # For now, will rely on the redirect.

    def test_user_list_view_authenticated_staff_get(self):
        self.client.login(username=self.staff_user.username, password='password123')
        response = self.client.get(self.user_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/user_list.html')
        self.assertIn('users', response.context)
        self.assertEqual(len(response.context['users']), User.objects.count()) # Should list all users
        self.assertEqual(response.context['search_query'], '')
        
        # Test ordering (by username)
        usernames_in_context = [u.username for u in response.context['users']]
        expected_usernames = sorted([self.staff_user.username, self.regular_user.username])
        self.assertEqual(usernames_in_context, expected_usernames)


    def test_user_list_view_search(self):
        self.client.login(username=self.staff_user.username, password='password123')
        
        # Search by username
        response = self.client.get(self.user_list_url, {'search': 'staffuser_view'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['users']), 1)
        self.assertEqual(response.context['users'][0], self.staff_user)
        self.assertEqual(response.context['search_query'], 'staffuser_view')

        # Search by email
        response = self.client.get(self.user_list_url, {'search': 'regular_view@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['users']), 1)
        self.assertEqual(response.context['users'][0], self.regular_user)

        # Search by department
        response = self.client.get(self.user_list_url, {'search': 'IT'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['users']), 1)
        self.assertEqual(response.context['users'][0], self.staff_user)
        
        # Search no results
        response = self.client.get(self.user_list_url, {'search': 'nonexistentxyz'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['users']), 0)

    def test_user_list_view_pagination(self):
        self.client.login(username=self.staff_user.username, password='password123')
        # Create more users to trigger pagination
        for i in range(15):
            User.objects.create_user(username=f'testuser{i}', password='password')
        
        response = self.client.get(self.user_list_url) # Default page 1
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        # Default paginate_by is 10 for UserListView
        self.assertEqual(len(response.context['users']), 10)

        response_page2 = self.client.get(self.user_list_url, {'page': 2})
        self.assertEqual(response_page2.status_code, 200)
        # 2 from setUp + 15 new = 17 total. Page 1 has 10, Page 2 has 7.
        self.assertEqual(len(response_page2.context['users']), 7)


class UserCreateViewTests(UserViewTestBase):
    def test_user_create_view_unauthenticated_get(self):
        response = self.client.get(self.user_create_url)
        expected_redirect_url = f"{self.login_url}?next={self.user_create_url}"
        self.assertRedirects(response, expected_redirect_url)

    def test_user_create_view_authenticated_non_staff_get(self):
        self.client.login(username=self.regular_user.username, password='password123')
        response = self.client.get(self.user_create_url)
        expected_redirect_url = f"{self.login_url}?next={self.user_create_url}"
        self.assertRedirects(response, expected_redirect_url)

    def test_user_create_view_authenticated_staff_get(self):
        self.client.login(username=self.staff_user.username, password='password123')
        response = self.client.get(self.user_create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/user_form.html')
        self.assertIsInstance(response.context['form'], CustomUserCreationForm)

    @patch('django.contrib.messages.success')
    def test_user_create_view_post_valid_non_ajax(self, mock_messages_success):
        self.client.login(username=self.staff_user.username, password='password123')
        initial_user_count = User.objects.count()
        data = {
            'username': 'newcreateduser', 'email': 'new@example.com', 
            'password1': 'StrongP@ss1', 'password2': 'StrongP@ss1',
            'department': 'HR', 'phone_number': '12345', 'is_staff': False
        }
        response = self.client.post(self.user_create_url, data)
        
        self.assertEqual(User.objects.count(), initial_user_count + 1)
        new_user = User.objects.get(username='newcreateduser')
        self.assertEqual(new_user.userprofile.department, 'HR')
        self.assertRedirects(response, self.user_list_url)
        mock_messages_success.assert_called_once() # Check if success message was called

    def test_user_create_view_post_valid_ajax(self):
        self.client.login(username=self.staff_user.username, password='password123')
        initial_user_count = User.objects.count()
        data = {
            'username': 'ajaxuser', 'email': 'ajax@example.com', 
            'password1': 'StrongP@ss1', 'password2': 'StrongP@ss1',
            'department': 'AJAX Dept', 'phone_number': '98765', 'is_staff': True
        }
        response = self.client.post(self.user_create_url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'success'})
        self.assertEqual(User.objects.count(), initial_user_count + 1)
        new_user = User.objects.get(username='ajaxuser')
        self.assertEqual(new_user.userprofile.department, 'AJAX Dept')

    def test_user_create_view_post_invalid_non_ajax(self):
        self.client.login(username=self.staff_user.username, password='password123')
        initial_user_count = User.objects.count()
        data = {'username': '', 'email': 'bad'} # Invalid data
        response = self.client.post(self.user_create_url, data)
        
        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertTemplateUsed(response, 'users/user_form.html')
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(User.objects.count(), initial_user_count)

    def test_user_create_view_post_invalid_ajax(self):
        self.client.login(username=self.staff_user.username, password='password123')
        data = {'username': '', 'email': 'bad_ajax'}
        response = self.client.post(self.user_create_url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200) # FormMixin returns 200 for invalid AJAX form
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn('errors', json_response)
        self.assertIn('username', json_response['errors'])

    @patch('django.contrib.messages.error')
    def test_user_create_view_post_username_integrity_error_non_ajax(self, mock_messages_error):
        self.client.login(username=self.staff_user.username, password='password123')
        data = {
            'username': self.staff_user.username, # Existing username
            'email': 'new@example.com', 'password1': 'Pass123!', 'password2': 'Pass123!',
        }
        # Mock form.save() to raise IntegrityError to simulate race condition if form validation passed
        # but DB constraint hit. Or rely on form's own username uniqueness validation.
        # CustomUserCreationForm already validates username uniqueness.
        response = self.client.post(self.user_create_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/user_form.html')
        self.assertIn('username', response.context['form'].errors)
        self.assertIn('A user with that username already exists.', str(response.context['form'].errors['username']))

    def test_user_create_view_post_username_integrity_error_ajax(self):
        self.client.login(username=self.staff_user.username, password='password123')
        data = {
            'username': self.staff_user.username, 'email': 'new_ajax@example.com',
            'password1': 'Pass123!', 'password2': 'Pass123!',
        }
        response = self.client.post(self.user_create_url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn('errors', json_response)
        self.assertIn('username', json_response['errors'])
        self.assertIn('A user with that username already exists.', str(json_response['errors']['username']))


class UserUpdateViewTests(UserViewTestBase):
    def test_user_update_view_unauthenticated_get(self):
        response = self.client.get(self.user_update_url)
        expected_redirect_url = f"{self.login_url}?next={self.user_update_url}"
        self.assertRedirects(response, expected_redirect_url)

    def test_user_update_view_authenticated_non_staff_get(self):
        self.client.login(username=self.regular_user.username, password='password123')
        # Non-staff trying to update another user (self.regular_user in this case, which is fine)
        # But AdminRequiredMixin should still prevent access to the view itself.
        response = self.client.get(self.user_update_url)
        expected_redirect_url = f"{self.login_url}?next={self.user_update_url}"
        self.assertRedirects(response, expected_redirect_url)

    def test_user_update_view_authenticated_staff_get_exists(self):
        self.client.login(username=self.staff_user.username, password='password123')
        response = self.client.get(self.user_update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/user_form.html')
        self.assertIsInstance(response.context['form'], CustomUserChangeForm)
        self.assertEqual(response.context['form'].instance, self.regular_user)

    def test_user_update_view_get_non_existent_pk(self):
        self.client.login(username=self.staff_user.username, password='password123')
        non_existent_url = reverse('users:user-update', kwargs={'pk': 99999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)

    @patch('django.contrib.messages.success')
    def test_user_update_view_post_valid_non_ajax(self, mock_messages_success):
        self.client.login(username=self.staff_user.username, password='password123')
        data = {
            'username': self.regular_user.username, # Cannot change username in UserChangeForm typically
            'email': 'updated_regular@example.com', 
            'department': 'Marketing', 'phone_number': '5551234', 'is_staff': True,
            'password': '', 'password_confirm': '' # No password change
        }
        response = self.client.post(self.user_update_url, data)
        
        self.assertRedirects(response, self.user_list_url)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, 'updated_regular@example.com')
        self.assertTrue(self.regular_user.is_staff)
        self.assertEqual(self.regular_user.userprofile.department, 'Marketing')
        mock_messages_success.assert_called_once()

    def test_user_update_view_post_valid_ajax(self):
        self.client.login(username=self.staff_user.username, password='password123')
        data = {
            'username': self.regular_user.username, 'email': 'updated_ajax@example.com', 
            'department': 'Sales AJAX', 'phone_number': '98700', 'is_staff': False
        }
        response = self.client.post(self.user_update_url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'success'})
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, 'updated_ajax@example.com')
        self.assertFalse(self.regular_user.is_staff)

    def test_user_update_view_post_invalid_non_ajax(self):
        self.client.login(username=self.staff_user.username, password='password123')
        data = {'email': 'bademailformat'} # Invalid email
        response = self.client.post(self.user_update_url, data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/user_form.html')
        self.assertTrue(response.context['form'].errors)

    def test_user_update_view_post_invalid_ajax(self):
        self.client.login(username=self.staff_user.username, password='password123')
        data = {'email': 'bad_ajax_email'}
        response = self.client.post(self.user_update_url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn('errors', json_response)
        self.assertIn('email', json_response['errors'])


class UserDeleteViewTests(UserViewTestBase):
    def setUp(self):
        super().setUp()
        self.user_to_delete = User.objects.create_user(username='todelete', password='password')
        self.delete_target_url = reverse('users:user-delete', kwargs={'pk': self.user_to_delete.pk})

    def test_user_delete_view_unauthenticated_get(self):
        response = self.client.get(self.delete_target_url)
        expected_redirect_url = f"{self.login_url}?next={self.delete_target_url}"
        self.assertRedirects(response, expected_redirect_url)

    def test_user_delete_view_authenticated_non_staff_get(self):
        self.client.login(username=self.regular_user.username, password='password123')
        response = self.client.get(self.delete_target_url)
        expected_redirect_url = f"{self.login_url}?next={self.delete_target_url}"
        self.assertRedirects(response, expected_redirect_url)

    def test_user_delete_view_authenticated_staff_get(self):
        self.client.login(username=self.staff_user.username, password='password123')
        response = self.client.get(self.delete_target_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/user_confirm_delete.html')
        self.assertEqual(response.context['object'], self.user_to_delete)

    def test_user_delete_view_get_ajax_not_allowed(self):
        self.client.login(username=self.staff_user.username, password='password123')
        response = self.client.get(self.delete_target_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {'status': 'error', 'message': 'Method not allowed.'})

    @patch('django.contrib.messages.success')
    def test_user_delete_view_post_non_ajax(self, mock_messages_success):
        self.client.login(username=self.staff_user.username, password='password123')
        initial_user_count = User.objects.count()
        response = self.client.post(self.delete_target_url)
        
        self.assertRedirects(response, self.user_list_url)
        self.assertEqual(User.objects.count(), initial_user_count - 1)
        self.assertFalse(User.objects.filter(pk=self.user_to_delete.pk).exists())
        mock_messages_success.assert_called_once()

    def test_user_delete_view_post_ajax(self):
        self.client.login(username=self.staff_user.username, password='password123')
        initial_user_count = User.objects.count()
        response = self.client.post(self.delete_target_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'success'})
        self.assertEqual(User.objects.count(), initial_user_count - 1)
        self.assertFalse(User.objects.filter(pk=self.user_to_delete.pk).exists())

    @patch('django.contrib.auth.models.User.delete') # Mock the delete method on the User model
    @patch('users.views.logger') # Mock the logger in users.views
    def test_user_delete_view_post_ajax_exception_during_delete(self, mock_logger, mock_user_delete):
        self.client.login(username=self.staff_user.username, password='password123')
        mock_user_delete.side_effect = Exception("DB error on delete")
        
        response = self.client.post(self.delete_target_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200) # The view returns 200 even on error for AJAX
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn("Error deleting user", json_response['message'])
        
        mock_logger.error.assert_called_once()
        self.assertIn(f"Error deleting user {self.user_to_delete.username}", mock_logger.error.call_args[0][0])
        # Ensure user was not actually deleted from DB due to mocked delete
        self.assertTrue(User.objects.filter(pk=self.user_to_delete.pk).exists())
        profile = UserProfile.objects.get(user=user)
        profile.date_format_preference = 'jalali' # Make a change to the profile
        profile.save()

        # Save the user again
        user.first_name = 'SignalTest'
        user.save()

        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1) # Should still be 1
        profile.refresh_from_db()
        self.assertEqual(profile.date_format_preference, 'jalali') # Original profile data should be intact

    def test_signals_interaction_only_one_profile_created(self):
        """ Test that when a new User is created, only one UserProfile is made despite two signals. """
        # Both signals are connected by default in apps.py
        self.assertEqual(UserProfile.objects.count(), 0)
        user = User.objects.create_user(**self.user_data)
        # The `get_or_create` logic in both signals should prevent duplicates.
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
        
        # Try saving again to ensure no duplicates
        user.last_name = "TestLastName"
        user.save()
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
