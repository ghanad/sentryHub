from django.test import TestCase, Client
from django.urls import reverse

from django.contrib.auth.models import User
from django.conf import settings

class CoreViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.home_url = reverse('core:home')
        self.about_url = reverse('core:about')
        self.dashboard_url = reverse('dashboard:dashboard') # Assuming 'dashboard' is the app name for dashboard
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_home_view_authenticated_user(self):
        """ Test GET request to home view by an authenticated user redirects to dashboard. """
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.home_url)
        self.assertRedirects(response, self.dashboard_url, fetch_redirect_response=False)

    def test_home_view_unauthenticated_user(self):
        """ Test GET request to home view by an unauthenticated user redirects to login page. """
        response = self.client.get(self.home_url)
        expected_redirect_url = f"{settings.LOGIN_URL}?next={self.home_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)
        # Ensure the status code of the redirect itself is 302
        self.assertEqual(response.status_code, 302)


    def test_about_view_get_request(self):
        """ Test GET request to about view returns 200 OK and correct template. """
        response = self.client.get(self.about_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/about.html')
        # Verify context is passed (even if it's just the default from TemplateView)
        self.assertIsNotNone(response.context)
        # If there are specific context variables expected, they can be checked here.
        # For a simple TemplateView, 'view' is usually in the context.
        self.assertIn('view', response.context)

from django.http import HttpResponse
from django.contrib.messages import get_messages
from unittest.mock import MagicMock, patch
from core.middleware import AdminAccessMiddleware # Adjust import path as necessary

# Dummy view for testing middleware
def dummy_view(request):
    return HttpResponse("OK")

# URLs for testing
# Note: We need to ensure these URLs are actually routed in a urls.py somewhere
# for the test client to work with them. For middleware testing, often the path
# itself is what the middleware logic keys off, not necessarily a valid view.
# However, Django's test client resolves URLs, so we need valid or mocked routing.
# For simplicity, we'll use existing URLs where possible and be mindful if a URL
# doesn't resolve, the error would be different before even hitting the middleware.

# Let's assume 'admin:index' is a valid admin URL.
# For custom admin paths, they would need to be in a URL conf.
# We will use paths directly and mock get_response to bypass actual view rendering.

class AdminAccessMiddlewareTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url_name = 'login' # As used in the middleware
        # Try to reverse 'login'. If it fails, it means it's not defined globally.
        # We might need to adjust this if the project uses a namespaced login URL like 'users:login'.
        try:
            self.login_url = reverse(self.login_url_name)
        except Exception:
            # Fallback if 'login' is not a global name. This might indicate a config issue
            # in the project or the middleware's assumption.
            # For now, let's assume 'users:login' as per settings.LOGIN_URL structure.
            # The actual middleware uses reverse('login'), so this test should reflect that.
            # If reverse('login') fails, the middleware itself has an issue.
            # We'll proceed assuming reverse('login') is intended to work.
            self.login_url = settings.LOGIN_URL 


        self.admin_urls_to_test = [
            '/admin/', # Standard admin
            '/admin-dashboard/somepage/', # Custom admin-like path
            '/users/list/', # Custom admin-like path
            # Add more specific admin paths if available and relevant
        ]
        
        self.non_admin_urls_to_test = [
            reverse('core:about'), # Assuming 'core:about' exists
            self.dashboard_url, # from CoreViewsTest setUp
            # Add more non-admin paths
        ]
        if hasattr(settings, 'HOME_URL') and settings.HOME_URL:
             self.non_admin_urls_to_test.append(settings.HOME_URL) # Usually '/'
        else:
            self.non_admin_urls_to_test.append('/')


        self.regular_user = User.objects.create_user(username='testuser', password='password123', is_staff=False)
        self.staff_user = User.objects.create_user(username='staffuser', password='password123', is_staff=True)
        
        # The middleware is instantiated per request, so we don't store an instance of it here.
        # We will test its effect by making requests.
        # To isolate middleware logic, we can mock get_response.

    def _get_middleware_response(self, request_path, user=None):
        """ Helper to simulate a request through the middleware. """
        mock_request = MagicMock()
        mock_request.path = request_path
        mock_request.user = user if user else MagicMock(is_authenticated=False)
        
        # Mock get_response to return a dummy HttpResponse
        # This allows us to check if get_response was called (meaning middleware allowed request)
        # or if the middleware returned a redirect itself.
        mock_get_response_func = MagicMock(return_value=HttpResponse("Mocked get_response"))
        
        middleware = AdminAccessMiddleware(mock_get_response_func)
        response = middleware(mock_request)
        return response, mock_get_response_func

    @patch('core.middleware.messages') # Patch messages where it's used in the middleware
    def test_admin_urls_unauthenticated_user(self, mock_messages):
        """ Test unauthenticated access to admin URLs. """
        unauthenticated_user = MagicMock(is_authenticated=False)
        for admin_path in self.admin_urls_to_test:
            response, mock_get_response = self._get_middleware_response(admin_path, user=unauthenticated_user)
            
            self.assertEqual(response.status_code, 302) # Redirect status
            # Check if the redirect URL is the login URL with the 'next' parameter
            # The actual middleware uses reverse('login') without a namespace.
            # If settings.LOGIN_URL is '/users/login/', and 'login' is namespaced as 'users:login',
            # then reverse('login') might fail or point elsewhere.
            # Assuming the middleware's reverse('login') works as intended to point to settings.LOGIN_URL
            
            # The middleware redirects to reverse('login') + f"?next={request.path}"
            # self.login_url is already reversed in setUp.
            expected_redirect_url = f"{self.login_url}?next={admin_path}"
            
            # The response from _get_middleware_response is a Django HttpResponseRedirect
            self.assertEqual(response.url, expected_redirect_url)
            mock_messages.error.assert_called_with(
                unauthenticated_user, # The request object in middleware is the user here
                "You do not have permission to access this page. Please log in with a staff account."
            )
            mock_get_response.assert_not_called() # Should not reach the actual view
            mock_messages.reset_mock() # Reset for the next iteration

    @patch('core.middleware.messages')
    def test_admin_urls_authenticated_non_staff_user(self, mock_messages):
        """ Test authenticated non-staff access to admin URLs. """
        self.regular_user.is_authenticated = True # MagicMock needs this for the if request.user.is_authenticated check
        for admin_path in self.admin_urls_to_test:
            response, mock_get_response = self._get_middleware_response(admin_path, user=self.regular_user)
            
            self.assertEqual(response.status_code, 302)
            expected_redirect_url = f"{self.login_url}?next={admin_path}"
            self.assertEqual(response.url, expected_redirect_url)
            mock_messages.error.assert_called_with(
                self.regular_user, 
                "You do not have permission to access this page. Please log in with a staff account."
            )
            mock_get_response.assert_not_called()
            mock_messages.reset_mock()

    @patch('core.middleware.messages')
    def test_admin_urls_authenticated_staff_user(self, mock_messages):
        """ Test authenticated staff access to admin URLs. """
        self.staff_user.is_authenticated = True
        for admin_path in self.admin_urls_to_test:
            response, mock_get_response = self._get_middleware_response(admin_path, user=self.staff_user)
            
            # Expect the middleware to call get_response, which returns our dummy "Mocked get_response"
            self.assertEqual(response.content.decode(), "Mocked get_response")
            self.assertEqual(response.status_code, 200) # Our dummy HttpResponse is 200
            mock_get_response.assert_called_once() # Ensures the view would have been processed
            mock_messages.error.assert_not_called() # No error messages for staff
            
            # Reset mocks for the next iteration if any were called
            mock_get_response.reset_mock()
            mock_messages.reset_mock()

    @patch('core.middleware.messages')
    def test_non_admin_urls_unauthenticated_user(self, mock_messages):
        """ Test unauthenticated access to non-admin URLs. """
        unauthenticated_user = MagicMock(is_authenticated=False)
        for non_admin_path in self.non_admin_urls_to_test:
            # Skip the login URL itself if it's in the list, as it would cause a redirect loop or different behavior
            if non_admin_path == self.login_url or non_admin_path == settings.LOGIN_URL:
                continue

            response, mock_get_response = self._get_middleware_response(non_admin_path, user=unauthenticated_user)
            
            self.assertEqual(response.content.decode(), "Mocked get_response")
            mock_get_response.assert_called_once()
            mock_messages.error.assert_not_called()
            mock_get_response.reset_mock()

    @patch('core.middleware.messages')
    def test_non_admin_urls_authenticated_non_staff_user(self, mock_messages):
        """ Test authenticated non-staff access to non-admin URLs. """
        self.regular_user.is_authenticated = True
        for non_admin_path in self.non_admin_urls_to_test:
            if non_admin_path == self.login_url or non_admin_path == settings.LOGIN_URL:
                continue

            response, mock_get_response = self._get_middleware_response(non_admin_path, user=self.regular_user)
            
            self.assertEqual(response.content.decode(), "Mocked get_response")
            mock_get_response.assert_called_once()
            mock_messages.error.assert_not_called()
            mock_get_response.reset_mock()

    @patch('core.middleware.messages')
    def test_non_admin_urls_authenticated_staff_user(self, mock_messages):
        """ Test authenticated staff access to non-admin URLs. """
        self.staff_user.is_authenticated = True
        for non_admin_path in self.non_admin_urls_to_test:
            if non_admin_path == self.login_url or non_admin_path == settings.LOGIN_URL:
                continue
                
            response, mock_get_response = self._get_middleware_response(non_admin_path, user=self.staff_user)
            
            self.assertEqual(response.content.decode(), "Mocked get_response")
            mock_get_response.assert_called_once()
            mock_messages.error.assert_not_called()
            mock_get_response.reset_mock()

    def test_access_login_page_unauthenticated(self):
        """ Test unauthenticated access to the login page itself. """
        unauthenticated_user = MagicMock(is_authenticated=False)
        # Assuming self.login_url is correctly resolved, e.g., to '/users/login/'
        response, mock_get_response = self._get_middleware_response(self.login_url, user=unauthenticated_user)
        self.assertEqual(response.content.decode(), "Mocked get_response") # Should pass through
        mock_get_response.assert_called_once()
        
    def test_access_login_page_authenticated_non_staff(self):
        """ Test authenticated non-staff access to the login page. """
        self.regular_user.is_authenticated = True
        response, mock_get_response = self._get_middleware_response(self.login_url, user=self.regular_user)
        self.assertEqual(response.content.decode(), "Mocked get_response") # Should pass through
        mock_get_response.assert_called_once()
        
    def test_access_login_page_authenticated_staff(self):
        """ Test authenticated staff access to the login page. """
        self.staff_user.is_authenticated = True
        response, mock_get_response = self._get_middleware_response(self.login_url, user=self.staff_user)
        self.assertEqual(response.content.decode(), "Mocked get_response") # Should pass through
        mock_get_response.assert_called_once()

from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib import messages
from core.context_processors import notifications # Adjust import path

class NotificationsContextProcessorTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request_with_messages(self):
        """ Helper to create a request object with a message storage. """
        request = self.factory.get('/')
        # Attach a message storage backend to the request
        setattr(request, 'session', MagicMock()) # Messages middleware often relies on session
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)
        return request

    def test_notifications_context_no_messages(self):
        """ Test context processor when there are no messages. """
        request = self._get_request_with_messages()
        context = notifications(request)
        self.assertIn('django_messages', context)
        self.assertEqual(context['django_messages'], [])

    def test_notifications_context_with_messages(self):
        """ Test context processor with messages of different levels and extra_tags. """
        request = self._get_request_with_messages()
        
        messages.add_message(request, messages.SUCCESS, "Operation successful!", extra_tags="tag1 tag2")
        messages.add_message(request, messages.ERROR, "An error occurred.")
        messages.add_message(request, messages.INFO, "Some information.", extra_tags="info-tag")
        messages.add_message(request, messages.WARNING, "Warning: proceed with caution.", extra_tags="special_warning")

        context = notifications(request)
        self.assertIn('django_messages', context)
        
        processed_messages = context['django_messages']
        self.assertEqual(len(processed_messages), 4)

        # Verify first message (SUCCESS)
        self.assertEqual(processed_messages[0]['level'], 'success') # Default level tag for SUCCESS
        self.assertEqual(processed_messages[0]['message'], "Operation successful!")
        self.assertEqual(processed_messages[0]['extra_tags'], "tag1 tag2")

        # Verify second message (ERROR)
        self.assertEqual(processed_messages[1]['level'], 'error')
        self.assertEqual(processed_messages[1]['message'], "An error occurred.")
        self.assertEqual(processed_messages[1]['extra_tags'], '') # No extra tags

        # Verify third message (INFO)
        self.assertEqual(processed_messages[2]['level'], 'info')
        self.assertEqual(processed_messages[2]['message'], "Some information.")
        self.assertEqual(processed_messages[2]['extra_tags'], "info-tag")
        
        # Verify fourth message (WARNING)
        self.assertEqual(processed_messages[3]['level'], 'warning')
        self.assertEqual(processed_messages[3]['message'], "Warning: proceed with caution.")
        self.assertEqual(processed_messages[3]['extra_tags'], "special_warning")

    def test_notifications_context_message_order(self):
        """ Test that messages are in the correct order. """
        request = self._get_request_with_messages()
        
        msg1_content = "First message (info)"
        msg2_content = "Second message (success)"
        msg3_content = "Third message (error)"

        messages.add_message(request, messages.INFO, msg1_content)
        messages.add_message(request, messages.SUCCESS, msg2_content)
        messages.add_message(request, messages.ERROR, msg3_content)

        context = notifications(request)
        processed_messages = context['django_messages']
        
        self.assertEqual(len(processed_messages), 3)
        self.assertEqual(processed_messages[0]['message'], msg1_content)
        self.assertEqual(processed_messages[0]['level'], 'info')
        
        self.assertEqual(processed_messages[1]['message'], msg2_content)
        self.assertEqual(processed_messages[1]['level'], 'success')
        
        self.assertEqual(processed_messages[2]['message'], msg3_content)
        self.assertEqual(processed_messages[2]['level'], 'error')

from django.template import Template, Context
from django.utils.safestring import SafeString
from django.contrib.auth.models import Group, AnonymousUser
from django.forms import CharField, Form
from core.templatetags import core_tags # Adjust if your templatetags module is named differently
from datetime import datetime, timedelta, date

# For mocking user profile if date_format_preference is used
class MockUserProfile:
    def __init__(self, date_format_preference='gregorian'):
        self.date_format_preference = date_format_preference

class MockUserWithProfile(User):
    class Meta:
        proxy = True # So it doesn't create a new table

    @property
    def profile(self):
        if not hasattr(self, '_profile_instance'):
            self._profile_instance = MockUserProfile()
        return self._profile_instance


class CoreTemplateTagsTest(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = User.objects.create_user(username='tagtester', password='password')
        self.group1 = Group.objects.create(name='group1')
        self.user.groups.add(self.group1)

    # --- Tests for time_ago filter ---
    def test_time_ago_just_now(self):
        self.assertEqual(core_tags.time_ago(self.now - timedelta(seconds=5)), "just now")

    def test_time_ago_minutes(self):
        self.assertEqual(core_tags.time_ago(self.now - timedelta(minutes=5)), "5 minutes ago")
        self.assertEqual(core_tags.time_ago(self.now - timedelta(minutes=1)), "1 minute ago")

    def test_time_ago_hours(self):
        self.assertEqual(core_tags.time_ago(self.now - timedelta(hours=3)), "3 hours ago")
        self.assertEqual(core_tags.time_ago(self.now - timedelta(hours=1)), "1 hour ago")

    def test_time_ago_days(self):
        self.assertEqual(core_tags.time_ago(self.now - timedelta(days=4)), "4 days ago")
        self.assertEqual(core_tags.time_ago(self.now - timedelta(days=1)), "1 day ago")
        
    def test_time_ago_months(self):
        # Approx, month length varies
        self.assertEqual(core_tags.time_ago(self.now - timedelta(days=35)), "1 month ago")
        self.assertEqual(core_tags.time_ago(self.now - timedelta(days=70)), "2 months ago")

    def test_time_ago_years(self):
        self.assertEqual(core_tags.time_ago(self.now - timedelta(days=370)), "1 year ago")
        self.assertEqual(core_tags.time_ago(self.now - timedelta(days=365*2 + 10)), "2 years ago")

    def test_time_ago_none_or_empty(self):
        self.assertEqual(core_tags.time_ago(None), "")
        self.assertEqual(core_tags.time_ago(""), "")

    def test_time_ago_future_datetime(self):
        # Based on current logic, future dates become "just now" due to max(0, diff.total_seconds())
        self.assertEqual(core_tags.time_ago(self.now + timedelta(minutes=5)), "just now")

    def test_time_ago_non_datetime(self):
        self.assertEqual(core_tags.time_ago("not a datetime"), "")
        self.assertEqual(core_tags.time_ago(12345), "")

    # --- Tests for status_badge filter ---
    def test_status_badge_known_statuses(self):
        self.assertEqual(core_tags.status_badge('active'), '<span class="badge bg-success">active</span>')
        self.assertEqual(core_tags.status_badge('firing'), '<span class="badge bg-danger">firing</span>')
        self.assertEqual(core_tags.status_badge('resolved'), '<span class="badge bg-success">resolved</span>')
        self.assertEqual(core_tags.status_badge('pending'), '<span class="badge bg-warning text-dark">pending</span>')
        self.assertEqual(core_tags.status_badge('silenced'), '<span class="badge bg-secondary">silenced</span>')
        self.assertEqual(core_tags.status_badge('acknowledged'), '<span class="badge bg-info text-dark">acknowledged</span>')

    def test_status_badge_unknown_status(self):
        self.assertEqual(core_tags.status_badge('unknown_status'), '<span class="badge bg-light text-dark">unknown_status</span>')

    def test_status_badge_case_insensitivity(self):
        self.assertEqual(core_tags.status_badge('FIRING'), '<span class="badge bg-danger">FIRING</span>')
        self.assertEqual(core_tags.status_badge('Active'), '<span class="badge bg-success">Active</span>')

    def test_status_badge_is_safe(self):
        self.assertIsInstance(core_tags.status_badge('active'), SafeString)

    # --- Tests for jsonify filter ---
    def test_jsonify_dict(self):
        data = {'key': 'value', 'number': 123}
        self.assertEqual(core_tags.jsonify(data), '{"key": "value", "number": 123}')

    def test_jsonify_list(self):
        data = [1, 'two', {'three': 3.0}]
        self.assertEqual(core_tags.jsonify(data), '[1, "two", {"three": 3.0}]')

    def test_jsonify_none(self):
        self.assertEqual(core_tags.jsonify(None), 'null')

    def test_jsonify_basic_types(self):
        self.assertEqual(core_tags.jsonify("string"), '"string"')
        self.assertEqual(core_tags.jsonify(123), '123')
        self.assertEqual(core_tags.jsonify(True), 'true')
        self.assertEqual(core_tags.jsonify(False), 'false')
    
    def test_jsonify_non_serializable(self):
        class NonSerializable: pass
        # The filter catches TypeError and returns the repr of the object.
        obj = NonSerializable()
        self.assertEqual(core_tags.jsonify(obj), f'"{repr(obj)}"')


    # --- Tests for format_datetime filter ---
    @patch('core.templatetags.core_tags.logger') # Mock logger for this test
    @patch('core.templatetags.core_tags.force_jalali', None) # Simulate import failure
    def test_format_datetime_jalali_import_fails(self, mock_logger):
        dt = timezone.make_aware(datetime(2023, 10, 26, 14, 30))
        # Create a mock user with a profile that prefers Jalali
        mock_user_jalali_pref = MockUserWithProfile()
        mock_user_jalali_pref.profile.date_format_preference = 'jalali'
        
        # Since force_jalali is None, it should fall back to Gregorian
        formatted_date = core_tags.format_datetime(dt, user=mock_user_jalali_pref)
        self.assertEqual(formatted_date, "2023-10-26 14:30") # Default Gregorian format
        mock_logger.error.assert_called_once_with("Jalali date formatting library (jdatetime) not installed or not found.")

    def test_format_datetime_gregorian(self):
        dt = timezone.make_aware(datetime(2023, 10, 26, 14, 30, 15))
        user_gregorian = MockUserWithProfile(date_format_preference='gregorian')
        self.assertEqual(core_tags.format_datetime(dt, user=user_gregorian), "2023-10-26 14:30") # Default format
        self.assertEqual(core_tags.format_datetime(dt, user=user_gregorian, format_string="%Y/%m/%d %H:%M:%S"), "2023/10/26 14:30:15")
        self.assertEqual(core_tags.format_datetime(dt, format_string="%d-%b-%y %I:%M %p"), "26-Oct-23 02:30 PM")

    @patch('core.templatetags.core_tags.force_jalali')
    def test_format_datetime_jalali_preference(self, mock_force_jalali):
        mock_force_jalali.return_value = "mocked jalali date" # Simulate what force_jalali might return
        dt = timezone.make_aware(datetime(2023, 10, 26, 14, 30))
        user_jalali = MockUserWithProfile(date_format_preference='jalali')
        
        self.assertEqual(core_tags.format_datetime(dt, user=user_jalali), "mocked jalali date")
        mock_force_jalali.assert_called_once_with(dt, None) # No format_string passed

        mock_force_jalali.reset_mock()
        custom_format = "%Y-%m-%d"
        self.assertEqual(core_tags.format_datetime(dt, user=user_jalali, format_string=custom_format), "mocked jalali date")
        mock_force_jalali.assert_called_once_with(dt, custom_format)


    def test_format_datetime_none_or_invalid(self):
        self.assertEqual(core_tags.format_datetime(None), "")
        self.assertEqual(core_tags.format_datetime("not a date"), "")
        self.assertEqual(core_tags.format_datetime(12345), "")
        
    def test_format_datetime_naive_datetime(self):
        dt_naive = datetime(2023, 10, 26, 14, 30)
        # Assuming default timezone is UTC for consistency in tests or that the filter handles it
        # For this test, let's just ensure it doesn't crash and produces a string
        # The filter makes it timezone-aware using settings.TIME_ZONE
        with patch.object(settings, 'TIME_ZONE', 'UTC'): # Ensure consistent timezone for test
            formatted_date = core_tags.format_datetime(dt_naive)
            self.assertIn("2023-10-26", formatted_date) # Check basic formatting

    # --- Tests for has_group filter ---
    def test_has_group_user_in_group_name(self):
        self.assertTrue(core_tags.has_group(self.user, 'group1'))

    def test_has_group_user_not_in_group_name(self):
        self.assertFalse(core_tags.has_group(self.user, 'nonexistent_group'))

    def test_has_group_user_in_group_object(self):
        self.assertTrue(core_tags.has_group(self.user, self.group1))

    def test_has_group_user_not_in_group_object(self):
        group2 = Group.objects.create(name='group2')
        self.assertFalse(core_tags.has_group(self.user, group2))

    def test_has_group_anonymous_user(self):
        anon_user = AnonymousUser()
        self.assertFalse(core_tags.has_group(anon_user, 'group1'))
        self.assertFalse(core_tags.has_group(anon_user, self.group1))

    def test_has_group_user_is_none(self):
        self.assertFalse(core_tags.has_group(None, 'group1'))

    def test_has_group_group_does_not_exist_name(self):
        self.assertFalse(core_tags.has_group(self.user, 'fake_group_name'))

    # --- Tests for add_class filter ---
    def test_add_class_no_existing_classes(self):
        class SimpleForm(Form):
            name = CharField()
        form = SimpleForm()
        field = form['name'] # This is a BoundField
        rendered_field = core_tags.add_class(field, 'my-new-class another-class')
        self.assertIn('class="my-new-class another-class"', str(rendered_field))

    def test_add_class_with_existing_classes(self):
        class SimpleFormWithAttrs(Form):
            name = CharField(widget=CharField.widget(attrs={'class': 'initial-class'}))
        form = SimpleFormWithAttrs()
        field = form['name']
        rendered_field = core_tags.add_class(field, 'extra-class')
        self.assertIn('class="initial-class extra-class"', str(rendered_field))
        
    def test_add_class_multiple_new_classes(self):
        class SimpleForm(Form):
            name = CharField()
        form = SimpleForm()
        field = form['name']
        rendered_field = core_tags.add_class(field, 'class1 class2 class3')
        self.assertIn('class="class1 class2 class3"', str(rendered_field))

    # --- Tests for calculate_duration filter ---
    def test_calculate_duration_less_than_minute(self):
        past_time = self.now - timedelta(seconds=30)
        self.assertEqual(core_tags.calculate_duration(past_time), "0m")

    def test_calculate_duration_minutes(self):
        past_time = self.now - timedelta(minutes=5, seconds=15)
        self.assertEqual(core_tags.calculate_duration(past_time), "5m")

    def test_calculate_duration_hours_and_minutes(self):
        past_time = self.now - timedelta(hours=2, minutes=35)
        self.assertEqual(core_tags.calculate_duration(past_time), "2h 35m")

    def test_calculate_duration_days_and_hours(self):
        past_time = self.now - timedelta(days=3, hours=4, minutes=30)
        self.assertEqual(core_tags.calculate_duration(past_time), "3d 4h")
        
    def test_calculate_duration_just_over_day(self):
        past_time = self.now - timedelta(days=1, minutes=5)
        self.assertEqual(core_tags.calculate_duration(past_time), "1d 0h")


    def test_calculate_duration_future_time(self):
        future_time = self.now + timedelta(hours=1)
        self.assertEqual(core_tags.calculate_duration(future_time), "Starts soon")

    def test_calculate_duration_none_or_invalid(self):
        self.assertEqual(core_tags.calculate_duration(None), "-")
        self.assertEqual(core_tags.calculate_duration("not a datetime"), "-")
        self.assertEqual(core_tags.calculate_duration(12345), "-")

    def test_calculate_duration_naive_datetime(self):
        # Naive datetime, should be made aware by the filter using settings.TIME_ZONE
        naive_past_time = datetime.now() - timedelta(hours=1, minutes=15)
        with patch.object(settings, 'TIME_ZONE', 'UTC'): # Ensure consistent timezone for test
            # Test depends on how the filter assumes timezone for naive datetimes.
            # If it assumes UTC (common for Django settings.TIME_ZONE), and self.now is also UTC-based (from timezone.now())
            # then the calculation should be straightforward.
            # The filter calls timezone.make_aware(value, timezone.get_current_timezone())
            # So, it will use the project's current active timezone.
            # For testing, it's good to have this consistent.
            aware_past_time = timezone.make_aware(naive_past_time) # Make it aware for comparison if needed
            # The actual output will depend on the difference between this aware time and timezone.now()
            # Let's just check it produces a duration string, not '-' or error
            duration_str = core_tags.calculate_duration(naive_past_time)
            self.assertIn("1h 15m", duration_str) # Or similar based on exact timing

from core.templatetags import date_format_tags # Adjust import path
import jdatetime # For verifying Jalali dates

class DateFormatTagsTest(TestCase):
    def setUp(self):
        self.gregorian_dt_aware = timezone.make_aware(datetime(2023, 10, 26, 14, 30, 5))
        self.gregorian_dt_naive = datetime(2023, 10, 26, 14, 30, 5)
        self.gregorian_date_obj = date(2023, 10, 26)
        
        # Expected Jalali for 2023-10-26
        self.jalali_equiv_dt = jdatetime.datetime(1402, 8, 4, 14, 30, 5)
        self.jalali_equiv_date = jdatetime.date(1402, 8, 4)

        self.user_gregorian_pref = MockUserWithProfile(date_format_preference='gregorian')
        self.user_gregorian_pref.username = 'gregorianuser' # Add username for User model compatibility
        self.user_gregorian_pref.save()


        self.user_jalali_pref = MockUserWithProfile(date_format_preference='jalali')
        self.user_jalali_pref.username = 'jalaliuser'
        self.user_jalali_pref.save()

        self.user_no_pref = MockUserWithProfile(date_format_preference=None) # Simulate no explicit preference
        self.user_no_pref.username = 'noprefuser'
        self.user_no_pref.save()
        
        self.user_no_profile = User.objects.create_user(username='noprofileuser', password='password')
        
        self.anonymous_user = AnonymousUser()

        self.factory = RequestFactory()

    def _get_mock_context(self, user_obj):
        request = self.factory.get('/')
        request.user = user_obj
        return {'request': request}

    # --- Tests for to_jalali filter ---
    # Note: The filter name in the code is `to_jalali`, but the prompt also mentions `to_jalali_datetime`.
    # Assuming `to_jalali` is the one to test as per the provided tag code.

    def test_to_jalali_gregorian_preference_datetime_aware(self):
        context = self._get_mock_context(self.user_gregorian_pref)
        # Default format
        self.assertEqual(
            date_format_tags.to_jalali(context, self.gregorian_dt_aware), 
            "2023-10-26 14:30"
        )
        # Custom format
        self.assertEqual(
            date_format_tags.to_jalali(context, self.gregorian_dt_aware, "%Y/%m/%d %H:%M:%S"), 
            "2023/10/26 14:30:05"
        )

    def test_to_jalali_gregorian_preference_datetime_naive(self):
        context = self._get_mock_context(self.user_gregorian_pref)
        # Default format
        # Naive datetime is made aware by the filter using settings.TIME_ZONE
        with patch.object(settings, 'TIME_ZONE', 'UTC'):
            self.assertEqual(
                date_format_tags.to_jalali(context, self.gregorian_dt_naive), 
                "2023-10-26 14:30" 
            )

    def test_to_jalali_gregorian_preference_date_object(self):
        context = self._get_mock_context(self.user_gregorian_pref)
        self.assertEqual(
            date_format_tags.to_jalali(context, self.gregorian_date_obj),
            "2023-10-26"
        )

    def test_to_jalali_gregorian_preference_date_string(self):
        context = self._get_mock_context(self.user_gregorian_pref)
        self.assertEqual(
            date_format_tags.to_jalali(context, "2023-10-26"),
            "2023-10-26"
        )
        self.assertEqual(
            date_format_tags.to_jalali(context, "2023-10-26 10:30:00"), # Datetime string
            "2023-10-26 10:30"
        )

    def test_to_jalali_jalali_preference_datetime_aware(self):
        context = self._get_mock_context(self.user_jalali_pref)
        # Default format for Jalali
        self.assertEqual(
            date_format_tags.to_jalali(context, self.gregorian_dt_aware),
            "1402-08-04 14:30"
        )
        # Custom format for Jalali
        self.assertEqual(
            date_format_tags.to_jalali(context, self.gregorian_dt_aware, "%Y/%m/%d ساعت %H:%M"),
            "1402/08/04 ساعت 14:30"
        )

    def test_to_jalali_jalali_preference_date_object(self):
        context = self._get_mock_context(self.user_jalali_pref)
        self.assertEqual(
            date_format_tags.to_jalali(context, self.gregorian_date_obj),
            "1402-08-04"
        )
    
    def test_to_jalali_jalali_preference_date_string(self):
        context = self._get_mock_context(self.user_jalali_pref)
        # Input is a Gregorian date string, should convert to Jalali string
        self.assertEqual(
            date_format_tags.to_jalali(context, "2023-10-26"),
            "1402-08-04"
        )
        self.assertEqual(
            date_format_tags.to_jalali(context, "2023-10-26 10:30:00"),
            "1402-08-04 10:30"
        )

    def test_to_jalali_no_user_in_context(self):
        # No request.user, should default to Gregorian
        context_no_user = {'request': MagicMock(user=None)}
        self.assertEqual(
            date_format_tags.to_jalali(context_no_user, self.gregorian_dt_aware),
            "2023-10-26 14:30"
        )

    def test_to_jalali_user_no_profile(self):
        context = self._get_mock_context(self.user_no_profile) # User without a .profile attribute
        self.assertEqual(
            date_format_tags.to_jalali(context, self.gregorian_dt_aware),
            "2023-10-26 14:30"
        )

    def test_to_jalali_user_profile_no_preference(self):
        context = self._get_mock_context(self.user_no_pref) # User with profile but preference is None
        self.assertEqual(
            date_format_tags.to_jalali(context, self.gregorian_dt_aware),
            "2023-10-26 14:30"
        )
        
    def test_to_jalali_anonymous_user(self):
        context = self._get_mock_context(self.anonymous_user)
        self.assertEqual(
            date_format_tags.to_jalali(context, self.gregorian_dt_aware),
            "2023-10-26 14:30"
        )

    def test_to_jalali_input_none_or_empty(self):
        context = self._get_mock_context(self.user_gregorian_pref)
        self.assertEqual(date_format_tags.to_jalali(context, None), None)
        self.assertEqual(date_format_tags.to_jalali(context, ""), "")

    def test_to_jalali_input_invalid_date_string(self):
        context = self._get_mock_context(self.user_gregorian_pref)
        self.assertEqual(date_format_tags.to_jalali(context, "invalid-date"), "invalid-date")
        context_jalali = self._get_mock_context(self.user_jalali_pref)
        self.assertEqual(date_format_tags.to_jalali(context_jalali, "invalid-date-too"), "invalid-date-too")

    # --- Tests for force_jalali filter ---
    def test_force_jalali_datetime_aware(self):
        self.assertEqual(date_format_tags.force_jalali(self.gregorian_dt_aware), "1402-08-04 14:30")
        self.assertEqual(date_format_tags.force_jalali(self.gregorian_dt_aware, "%Y/%m/%d ساعت %H:%M:%S"), "1402/08/04 ساعت 14:30:05")

    def test_force_jalali_datetime_naive(self):
        with patch.object(settings, 'TIME_ZONE', 'UTC'):
            self.assertEqual(date_format_tags.force_jalali(self.gregorian_dt_naive), "1402-08-04 14:30")

    def test_force_jalali_date_object(self):
        self.assertEqual(date_format_tags.force_jalali(self.gregorian_date_obj), "1402-08-04")

    def test_force_jalali_date_string(self):
        self.assertEqual(date_format_tags.force_jalali("2023-10-26"), "1402-08-04")
        self.assertEqual(date_format_tags.force_jalali("2023-10-26 10:30"), "1402-08-04 10:30")


    def test_force_jalali_input_none_or_empty(self):
        self.assertEqual(date_format_tags.force_jalali(None), None)
        self.assertEqual(date_format_tags.force_jalali(""), "")

    def test_force_jalali_input_invalid_date_string(self):
        self.assertEqual(date_format_tags.force_jalali("invalid-date"), "invalid-date")
        
    # --- Tests for force_gregorian filter ---
    def test_force_gregorian_datetime_aware(self):
        self.assertEqual(date_format_tags.force_gregorian(self.gregorian_dt_aware), "2023-10-26 14:30")
        self.assertEqual(date_format_tags.force_gregorian(self.gregorian_dt_aware, "%Y/%m/%d %H:%M:%S"), "2023/10/26 14:30:05")

    def test_force_gregorian_datetime_naive(self):
        with patch.object(settings, 'TIME_ZONE', 'UTC'):
            self.assertEqual(date_format_tags.force_gregorian(self.gregorian_dt_naive), "2023-10-26 14:30")

    def test_force_gregorian_date_object(self):
        self.assertEqual(date_format_tags.force_gregorian(self.gregorian_date_obj), "2023-10-26")

    def test_force_gregorian_date_string(self):
        self.assertEqual(date_format_tags.force_gregorian("2023-10-26"), "2023-10-26")
        # Test with a Jalali date string input (should parse and convert)
        self.assertEqual(date_format_tags.force_gregorian("1402-08-04"), "2023-10-26")
        self.assertEqual(date_format_tags.force_gregorian("1402-08-04 10:30"), "2023-10-26 10:30")


    def test_force_gregorian_input_none_or_empty(self):
        self.assertEqual(date_format_tags.force_gregorian(None), None)
        self.assertEqual(date_format_tags.force_gregorian(""), "")

    def test_force_gregorian_input_invalid_date_string(self):
        self.assertEqual(date_format_tags.force_gregorian("invalid-date"), "invalid-date")