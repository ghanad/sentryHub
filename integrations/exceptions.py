class SlackNotificationError(Exception):
    """Custom exception for Slack notification failures that should trigger a retry."""
    pass