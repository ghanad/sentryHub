from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from .models import UserProfile

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    department = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    is_staff = forms.BooleanField(required=False, label='Admin Access', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

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
    department = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    is_staff = forms.BooleanField(required=False, label='Admin Access', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    password1 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to keep current password'}))
    password2 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to keep current password'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'is_staff', 'department', 'phone_number', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = 'Leave blank to keep current password'
        self.fields['password2'].help_text = 'Leave blank to keep current password'
        if self.instance.pk:
            try:
                profile = self.instance.profile
                self.fields['department'].initial = profile.department
                self.fields['phone_number'].initial = profile.phone_number
            except UserProfile.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 or password2:
            if not password1:
                self.add_error('password1', 'Please enter a new password')
            if not password2:
                self.add_error('password2', 'Please confirm the new password')
            if password1 and password2 and password1 != password2:
                self.add_error('password2', 'Passwords do not match')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password1 = self.cleaned_data.get('password1')
        if password1:
            user.set_password(password1)
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.department = self.cleaned_data['department']
            profile.phone_number = self.cleaned_data['phone_number']
            profile.save()
        return user 