# Generated by Django 3.2.20 on 2025-04-28 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='JiraIntegrationRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('match_criteria', models.JSONField(default=dict, help_text='JSON object defining label match criteria. E.g., {"job": "node", "severity": "critical"}')),
                ('jira_project_key', models.CharField(help_text='Target Jira project key (e.g., OPS)', max_length=50)),
                ('jira_issue_type', models.CharField(help_text='Target Jira issue type (e.g., Bug, Task)', max_length=50)),
                ('assignee', models.CharField(blank=True, help_text='Jira username to assign the issue to (leave blank for no assignment)', max_length=100)),
                ('jira_title_template', models.TextField(blank=True, default='Alert: {{ alertname }} for {{ job }}', help_text="Template for the Jira issue title. Use {{ label_name }} or {{ annotation_name }}. Default: 'Alert: {{ alertname }} for {{ job }}'")),
                ('jira_description_template', models.TextField(blank=True, default='Firing alert details:\nLabels:\n{% for key, value in labels.items() %}  {{ key }}: {{ value }}\n{% endfor %}\nAnnotations:\n{% for key, value in annotations.items() %}  {{ key }}: {{ value }}\n{% endfor %}', help_text='Template for the Jira issue description. Uses Django template syntax. Available context: labels (dict), annotations (dict), alertname, status, etc. See documentation for full context.')),
                ('jira_update_comment_template', models.TextField(blank=True, default="Alert status changed to {{ status }}. \n{% if status == 'firing' %}Labels:\n{% for key, value in labels.items() %}  {{ key }}: {{ value }}\n{% endfor %}{% endif %}", help_text='Template for the comment added when an existing Jira issue is updated (e.g., alert resolved or re-fired). Uses Django template syntax.')),
                ('priority', models.IntegerField(default=0, help_text='Higher priority rules are evaluated first.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('watchers', models.TextField(blank=True, help_text='Comma-separated list of Jira usernames to add as watchers (e.g., user1,user2,user3)')),
            ],
            options={
                'verbose_name': 'Jira Integration Rule',
                'verbose_name_plural': 'Jira Integration Rules',
                'ordering': ['-priority', 'name'],
            },
        ),
    ]
