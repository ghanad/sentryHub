# core/tests/test_templatetags.py

import json
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.utils.safestring import mark_safe
from django import forms 
from unittest.mock import patch, MagicMock
from core.templatetags import date_format_tags
import sys


# Assuming UserProfile model exists in users.models
# Adjust the import if your UserProfile model is elsewhere or not yet created
try:
    from users.models import UserProfile
except ImportError:
    UserProfile = None # Handle if UserProfile is not available yet

from core.templatetags import core_tags
from core.templatetags.core_tags import (
    time_ago,
    status_badge,
    jsonify,
    format_datetime, 
    has_group,
    add_class,
    calculate_duration
)


from core.templatetags.core_tags import (
    format_datetime 
)

# Mock for the force_jalali function to avoid dependency on date_format_tags.py during these tests
# We will test date_format_tags.py separately.
def mock_force_jalali(value, format_string="%Y-%m-%d %H:%M:%S"):
    if not value:
        return ""
    # Simulate a Jalali-like format for testing purposes
    return f"Jalali: {value.strftime(format_string)}"


class CoreTagsTimeAgoTests(TestCase):
    @patch('django.utils.timezone.now')
    def test_time_ago_just_now(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 30, tzinfo=timezone.utc)
        past_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(time_ago(past_time), "just now")

    @patch('django.utils.timezone.now')
    def test_time_ago_minutes(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        past_time_singular = datetime(2023, 1, 1, 12, 4, 0, tzinfo=timezone.utc)
        past_time_plural = datetime(2023, 1, 1, 12, 3, 0, tzinfo=timezone.utc)
        self.assertEqual(time_ago(past_time_singular), "1 minute ago")
        self.assertEqual(time_ago(past_time_plural), "2 minutes ago")

    @patch('django.utils.timezone.now')
    def test_time_ago_hours(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        past_time_singular = datetime(2023, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        past_time_plural = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(time_ago(past_time_singular), "1 hour ago")
        self.assertEqual(time_ago(past_time_plural), "2 hours ago")

    @patch('django.utils.timezone.now')
    def test_time_ago_days(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 3, 12, 0, 0, tzinfo=timezone.utc)
        past_time_singular = datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        past_time_plural = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(time_ago(past_time_singular), "1 day ago")
        self.assertEqual(time_ago(past_time_plural), "2 days ago")

    @patch('django.utils.timezone.now')
    def test_time_ago_months(self, mock_now):
        mock_now.return_value = datetime(2023, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
        past_time_singular = datetime(2023, 2, 10, 12, 0, 0, tzinfo=timezone.utc) # Approx 1 month
        past_time_plural = datetime(2023, 1, 10, 12, 0, 0, tzinfo=timezone.utc)   # Approx 2 months
        self.assertEqual(time_ago(past_time_singular), "1 month ago")
        self.assertEqual(time_ago(past_time_plural), "2 months ago")

    def test_time_ago_none_value(self):
        self.assertEqual(time_ago(None), "")


class CoreTagsStatusBadgeTests(TestCase):
    def test_status_badge_known_statuses(self):
        self.assertEqual(status_badge('active'), mark_safe('<span class="badge bg-success">active</span>'))
        self.assertEqual(status_badge('inactive'), mark_safe('<span class="badge bg-danger">inactive</span>'))
        self.assertEqual(status_badge('pending'), mark_safe('<span class="badge bg-warning">pending</span>'))
        self.assertEqual(status_badge('unknown'), mark_safe('<span class="badge bg-secondary">unknown</span>'))

    def test_status_badge_case_insensitivity(self):
        self.assertEqual(status_badge('Active'), mark_safe('<span class="badge bg-success">Active</span>'))

    def test_status_badge_unknown_status_defaults_to_secondary(self):
        self.assertEqual(status_badge('other_status'), mark_safe('<span class="badge bg-secondary">other_status</span>'))


class CoreTagsJsonifyTests(TestCase):
    def test_jsonify_none(self):
        self.assertEqual(jsonify(None), 'null')

    def test_jsonify_dict(self):
        data = {'key': 'value', 'number': 123, 'active': True, 'nested': {'a': 1}}
        expected_json = '{"key":"value","number":123,"active":true,"nested":{"a":1}}'
        self.assertEqual(jsonify(data), expected_json)

    def test_jsonify_list(self):
        data = [1, "string", False, None, {"obj": "inside"}]
        expected_json = '[1,"string",false,null,{"obj":"inside"}]'
        self.assertEqual(jsonify(data), expected_json)

    def test_jsonify_non_serializable_graceful_fallback(self):
        # datetime objects are not directly serializable by default json.dumps
        # The filter should catch TypeError and return 'null'
        data = datetime(2023, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(jsonify(data), 'null')

# Mock for the force_jalali function for testing format_datetime's logic
def mock_force_jalali_success_for_sys_modules(value, format_string="%Y-%m-%d %H:%M:%S"):
    if not value:
        return ""
    return f"JALALI_VIA_SYS_MODULES:{value.strftime(format_string)}"

# Mock for the force_jalali function for testing format_datetime's logic
def mock_jalali_conversion_success(value, format_string="%Y-%m-%d %H:%M:%S"):
    if not value:
        return ""
    return f"JALALI_CONVERTED:{value.strftime(format_string)}"

def mock_jalali_conversion_import_error(*args, **kwargs):
    raise AssertionError("mock_jalali_conversion_import_error should not have been called directly.")

def mock_force_jalali_success_patch(value, format_string="%Y-%m-%d %H:%M:%S"):
    if not value:
        return ""
    return f"JALALI_PATCHED:{value.strftime(format_string)}"


class CoreTagsFormatDatetimeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_datetime_utc = datetime(2023, 10, 26, 14, 30, 15, tzinfo=timezone.utc)
        cls.test_datetime_local_appearance = datetime(2023, 10, 26, 18, 0, 15) # Example

        cls.user_gregorian_ft = User.objects.create_user(username='gregorianuser_ft_date_v6')
        cls.user_jalali_ft = User.objects.create_user(username='jalaliuser_ft_date_v6')

        if UserProfile:
            try:
                profile_gregorian, _ = UserProfile.objects.get_or_create(user=cls.user_gregorian_ft)
                profile_gregorian.date_format_preference = 'gregorian'
                profile_gregorian.save()

                profile_jalali, _ = UserProfile.objects.get_or_create(user=cls.user_jalali_ft)
                profile_jalali.date_format_preference = 'jalali'
                profile_jalali.save()
            except Exception as e:
                print(f"Warning: Error setting up UserProfile in setUpTestData: {e}")

    def test_format_datetime_none_value(self):
        self.assertEqual(format_datetime(None), "")

    @patch('django.utils.timezone.localtime')
    def test_format_datetime_no_user_defaults_to_gregorian(self, mock_localtime):
        mock_localtime.return_value.strftime.return_value = "GREGORIAN_DEFAULT_FORMAT"
        self.assertEqual(format_datetime(self.test_datetime_utc), "GREGORIAN_DEFAULT_FORMAT")
        mock_localtime.assert_called_once_with(self.test_datetime_utc)

    @patch('django.utils.timezone.localtime')
    def test_format_datetime_user_prefers_gregorian(self, mock_localtime):
        if not UserProfile: self.skipTest("UserProfile model not available.")
        mock_localtime.return_value.strftime.return_value = "GREGORIAN_USER_FORMAT"
        self.assertEqual(format_datetime(self.test_datetime_utc, self.user_gregorian_ft), "GREGORIAN_USER_FORMAT")
        mock_localtime.assert_called_once_with(self.test_datetime_utc)

    # Patch the force_jalali function where it's defined and imported from
    @patch('core.templatetags.date_format_tags.force_jalali', new=mock_force_jalali_success_patch)
    @patch('django.utils.timezone.localtime') # Also mock localtime to check it's NOT called
    def test_format_datetime_user_prefers_jalali_force_jalali_succeeds(self, mock_localtime):
        if not UserProfile:
            self.skipTest("UserProfile model not available.")
        self.user_jalali_ft.profile.date_format_preference = 'jalali'
        self.user_jalali_ft.profile.save()
        expected_output = f"JALALI_PATCHED:{self.test_datetime_utc.strftime('%Y-%m-%d %H:%M:%S')}"
        self.assertEqual(format_datetime(self.test_datetime_utc, self.user_jalali_ft), expected_output)
        mock_localtime.assert_not_called()  # Should not call localtime if jalali path is taken

    @patch('core.templatetags.date_format_tags.force_jalali', side_effect=ImportError("Simulated import error for force_jalali"))
    @patch('django.utils.timezone.localtime')
    def test_format_datetime_user_prefers_jalali_force_jalali_import_fails(self, mock_localtime, mock_fj_import_error):
        if not UserProfile: self.skipTest("UserProfile model not available.")
        self.user_jalali_ft.profile.date_format_preference = 'jalali'
        self.user_jalali_ft.profile.save()
        mock_localtime.return_value.strftime.return_value = "GREGORIAN_FALLBACK_FORMAT"
        with self.assertLogs('core.templatetags.core_tags', level='ERROR') as cm:
            result = format_datetime(self.test_datetime_utc, self.user_jalali_ft)
        self.assertEqual(result, "GREGORIAN_FALLBACK_FORMAT")
        self.assertTrue(
            any("Could not import force_jalali from core.templatetags.date_format_tags: Simulated import error for force_jalali"
                in log_record.getMessage() for log_record in cm.records)
        )
        mock_localtime.assert_called_once_with(self.test_datetime_utc)

    @patch('django.utils.timezone.localtime')
    def test_format_datetime_with_custom_format_string_gregorian(self, mock_localtime):
        custom_format = "%d/%m/%Y"
        mock_localtime.return_value.strftime.return_value = f"GREGORIAN_CUSTOM:{custom_format}"
        self.assertEqual(format_datetime(self.test_datetime_utc, format_string=custom_format), f"GREGORIAN_CUSTOM:{custom_format}")
        mock_localtime.return_value.strftime.assert_called_once_with(custom_format)

    @patch('core.templatetags.date_format_tags.force_jalali', new=mock_force_jalali_success_patch)
    @patch('django.utils.timezone.localtime')
    def test_format_datetime_with_custom_format_string_jalali(self, mock_localtime):
        if not UserProfile:
            self.skipTest("UserProfile model not available.")
        self.user_jalali_ft.profile.date_format_preference = 'jalali'
        self.user_jalali_ft.profile.save()
        custom_format = "%d/%m/%Y"
        expected_output = f"JALALI_PATCHED:{self.test_datetime_utc.strftime(custom_format)}"
        self.assertEqual(
            format_datetime(self.test_datetime_utc, self.user_jalali_ft, format_string=custom_format),
            expected_output,
        )
        mock_localtime.assert_not_called()

    def test_format_datetime_exception_in_value_strftime(self):
        bad_value = "not-a-datetime-object"
        self.assertEqual(format_datetime(bad_value), str(bad_value))

    @patch('django.utils.timezone.localtime')
    def test_format_datetime_user_without_profile_instance(self, mock_localtime):
        user_no_profile = User.objects.create_user(username='no_profile_user_v6')
        # Assuming signal creates UserProfile with default 'gregorian'
        mock_localtime.return_value.strftime.return_value = "GREGORIAN_NO_PROFILE_FORMAT"
        self.assertEqual(format_datetime(self.test_datetime_utc, user_no_profile), "GREGORIAN_NO_PROFILE_FORMAT")
        mock_localtime.assert_called_once_with(self.test_datetime_utc)


class CoreTagsHasGroupTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1')
        self.user2 = User.objects.create_user(username='user2')
        self.group1 = Group.objects.create(name='group1')
        self.group2 = Group.objects.create(name='group2')
        self.user1.groups.add(self.group1)

    def test_has_group_user_in_group_by_string(self):
        self.assertTrue(has_group(self.user1, 'group1'))

    def test_has_group_user_not_in_group_by_string(self):
        self.assertFalse(has_group(self.user1, 'group2'))
        self.assertFalse(has_group(self.user2, 'group1'))

    def test_has_group_user_in_group_by_object(self):
        self.assertTrue(has_group(self.user1, self.group1))

    def test_has_group_user_not_in_group_by_object(self):
        self.assertFalse(has_group(self.user1, self.group2))

    def test_has_group_unauthenticated_user(self):
        unauthenticated_user = MagicMock(spec=User)
        unauthenticated_user.is_authenticated = False
        self.assertFalse(has_group(unauthenticated_user, 'group1'))

    def test_has_group_none_user(self):
        self.assertFalse(has_group(None, 'group1'))


class CoreTagsAddClassTests(TestCase):
    # Helper class to simulate a Django form field's widget
    class MockWidget(forms.Widget):
        def __init__(self, attrs=None):
            super().__init__(attrs)

        def render(self, name, value, attrs=None, renderer=None):
            # A simplified render for testing purposes, focusing on the class attribute
            final_attrs = {**(self.attrs or {}), **(attrs or {})}
            class_attr = final_attrs.get('class', '')
            return f'<input type="text" name="{name}" value="{value}" class="{class_attr}">'

    # Helper class to simulate a Django BoundField
    class MockBoundField:
        def __init__(self, initial_widget_attrs=None):
            # This 'field' attribute simulates the actual Field instance (e.g., CharField)
            self.field = MagicMock()
            self.field.widget = CoreTagsAddClassTests.MockWidget(attrs=initial_widget_attrs or {})
            self.field.widget.is_required = False # Default, can be overridden

        def as_widget(self, attrs=None):
            # Simulate how Django's BoundField.as_widget() calls widget.render()
            # passing updated attributes.
            return self.field.widget.render('test_name', 'test_value', attrs=attrs)

    def test_add_class_to_field_with_no_existing_classes(self):
        # Create an instance of our MockBoundField
        mock_bound_field_instance = self.MockBoundField()

        result_html = add_class(mock_bound_field_instance, 'new-class another-class')

        # The add_class filter modifies the widget's attrs directly
        self.assertEqual(mock_bound_field_instance.field.widget.attrs['class'], 'new-class another-class')
        # Check the rendered output (optional, but good for sanity check)
        self.assertIn('class="new-class another-class"', result_html)

    def test_add_class_to_field_with_existing_classes(self):
        mock_bound_field_instance = self.MockBoundField(initial_widget_attrs={'class': 'existing-one'})
        result_html = add_class(mock_bound_field_instance, 'new-class')

        self.assertEqual(mock_bound_field_instance.field.widget.attrs['class'], 'existing-one new-class')
        self.assertIn('class="existing-one new-class"', result_html)


class CoreTagsCalculateDurationTests(TestCase):
    @patch('django.utils.timezone.now')
    def test_calculate_duration_less_than_minute(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 30, tzinfo=timezone.utc)
        start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(calculate_duration(start_time), "<1m")

    @patch('django.utils.timezone.now')
    def test_calculate_duration_minutes(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 12, 5, 30, tzinfo=timezone.utc)
        start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc) # 5m 30s
        self.assertEqual(calculate_duration(start_time), "5m")

    @patch('django.utils.timezone.now')
    def test_calculate_duration_hours_and_minutes(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 14, 35, 0, tzinfo=timezone.utc)
        start_time = datetime(2023, 1, 1, 12, 5, 0, tzinfo=timezone.utc) # 2h 30m
        self.assertEqual(calculate_duration(start_time), "2h 30m")

    @patch('django.utils.timezone.now')
    def test_calculate_duration_days_and_hours(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 3, 14, 0, 0, tzinfo=timezone.utc)
        start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc) # 2d 2h
        self.assertEqual(calculate_duration(start_time), "2d 2h")

    @patch('django.utils.timezone.now')
    def test_calculate_duration_future_start_time(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        start_time = datetime(2023, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        self.assertEqual(calculate_duration(start_time), "Starts soon")

    def test_calculate_duration_invalid_input(self):
        self.assertEqual(calculate_duration("not a datetime"), "-")
        self.assertEqual(calculate_duration(None), "-")

    @patch('django.utils.timezone.now')
    def test_calculate_duration_naive_datetime_input(self, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 12, 10, 0, tzinfo=timezone.utc)
        # Naive datetime, assuming default timezone is UTC for the test environment
        # or that make_aware correctly converts it.
        start_time_naive = datetime(2023, 1, 1, 12, 0, 0)
        # If default_timezone is UTC, this becomes 2023-01-01 12:00:00+00:00
        # Duration should be 10m
        with patch('django.utils.timezone.get_default_timezone') as mock_get_default_tz:
            mock_get_default_tz.return_value = timezone.utc # Ensure consistent behavior
            self.assertEqual(calculate_duration(start_time_naive), "10m")

    @patch('django.utils.timezone.now')
    @patch('django.utils.timezone.make_aware', side_effect=Exception("Cannot make aware"))
    def test_calculate_duration_naive_datetime_make_aware_fails(self, mock_make_aware, mock_now):
        mock_now.return_value = datetime(2023, 1, 1, 12, 10, 0, tzinfo=timezone.utc)
        start_time_naive = datetime(2023, 1, 1, 12, 0, 0)
        self.assertEqual(calculate_duration(start_time_naive), "-")