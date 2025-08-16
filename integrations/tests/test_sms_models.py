from django.core.exceptions import ValidationError
from django.test import TestCase
from integrations.models import PhoneBook, SmsIntegrationRule


class SmsModelsTests(TestCase):
    def test_phonebook_str(self):
        pb = PhoneBook.objects.create(name='alice', phone_number='123')
        self.assertEqual(str(pb), 'alice: 123')

    def test_sms_rule_defaults_and_str(self):
        rule = SmsIntegrationRule.objects.create(
            name='r1',
            match_criteria={},
            recipients='alice',
            firing_template='hi',
        )
        self.assertEqual(str(rule), 'r1 (Active, Prio: 0)')
        self.assertTrue(rule.is_active)

    def test_match_criteria_must_be_dict(self):
        rule = SmsIntegrationRule(
            name='r2',
            match_criteria='no',
            firing_template='hi',
        )
        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_ordering(self):
        SmsIntegrationRule.objects.create(name='a', match_criteria={}, firing_template='x', priority=2)
        SmsIntegrationRule.objects.create(name='c', match_criteria={}, firing_template='x', priority=1)
        SmsIntegrationRule.objects.create(name='b', match_criteria={}, firing_template='x', priority=1)
        names = [r.name for r in SmsIntegrationRule.objects.all()]
        self.assertEqual(names, ['a', 'b', 'c'])
