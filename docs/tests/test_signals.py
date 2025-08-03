from django.test import TestCase
from django.contrib.auth import get_user_model
from alerts.models import AlertGroup
from docs.models import AlertDocumentation, DocumentationAlertGroup

User = get_user_model()

class HandleDocumentationSaveSignalTest(TestCase):
    def test_creates_link_when_title_matches_alert(self):
        user = User.objects.create_user(username='testuser', password='password')
        alert = AlertGroup.objects.create(
            fingerprint='fp1', name='Match Me', labels={},
            severity='critical', current_status='firing'
        )
        doc = AlertDocumentation.objects.create(
            title='Match Me', description='Desc', created_by=user
        )
        self.assertTrue(
            DocumentationAlertGroup.objects.filter(
                documentation=doc, alert_group=alert
            ).exists()
        )
