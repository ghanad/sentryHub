from django.db import migrations

def create_user_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('users', 'UserProfile')
    
    # Create profile for users that don't have one
    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),  # Make sure this matches your last migration
    ]

    operations = [
        migrations.RunPython(create_user_profiles),
    ] 