from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class UserProfile(models.Model):
    DATE_FORMAT_CHOICES = [
        ('gregorian', 'Gregorian (Western)'),
        ('jalali', 'Jalali (Persian)')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    timezone = models.CharField(
        max_length=64,
        default='UTC',
        help_text='Preferred timezone for displaying dates and resolving alerts'
    )
    date_format_preference = models.CharField(
        max_length=10,
        choices=DATE_FORMAT_CHOICES,
        default='gregorian',
        help_text='Choose your preferred date format'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
