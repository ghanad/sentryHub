from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from .models import UserProfile

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    department = forms.CharField(max_length=100, required=False)
    phone_number = forms.CharField(max_length=20, required=False)
    is_staff = forms.BooleanField(required=False, label='Admin Access')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'is_staff', 'department', 'phone_number')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'department': self.cleaned_data['department'],
                    'phone_number': self.cleaned_data['phone_number']
                }
            )
            if not created:
                profile.department = self.cleaned_data['department']
                profile.phone_number = self.cleaned_data['phone_number']
                profile.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    department = forms.CharField(max_length=100, required=False)
    phone_number = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'is_staff', 'department', 'phone_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            try:
                profile = self.instance.profile
                self.fields['department'].initial = profile.department
                self.fields['phone_number'].initial = profile.phone_number
            except UserProfile.DoesNotExist:
                pass

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.department = self.cleaned_data['department']
            profile.phone_number = self.cleaned_data['phone_number']
            profile.save()
        return user 