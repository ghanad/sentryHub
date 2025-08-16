class SlackNotificationError(Exception):
    """Custom exception for Slack notification failures that should trigger a retry."""
    pass


class SmsNotificationError(Exception):
    """Custom exception for SMS notification failures that should trigger a retry."""
    pass
