from django.test import TestCase
from docs.models import Macro
from docs.templatetags.macro_tags import apply_macros


class ApplyMacrosFilterTest(TestCase):
    def setUp(self):
        Macro.objects.create(key='DEV_PHONE', value='123456')
        Macro.objects.create(key='TEAM', value='SentryHub')

    def test_apply_macros_replaces_tokens(self):
        text = 'Call [[DEV_PHONE]] to reach the [[TEAM]] team.'
        result = apply_macros(text)
        self.assertEqual(result, 'Call 123456 to reach the SentryHub team.')

    def test_apply_macros_with_no_text(self):
        self.assertEqual(apply_macros(None), '')
