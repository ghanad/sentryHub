# Remove Recodes from Database with shell
```python
from alerts.models import AlertGroup, AlertInstance, AlertComment
from docs.models import AlertDocumentation, DocumentationAlertGroup
AlertInstance.objects.all().delete()
AlertComment.objects.all().delete()
DocumentationAlertGroup.objects.all().delete()
AlertGroup.objects.all().delete()
AlertDocumentation.objects.all().delete()
```

# Remove all comments from database
```python
from alerts.models import AlertComment
comments = AlertComment.objects.all()
for comment in comments:
    print(f"Deleting comment id {comment.id}")
    comment.delete()
```

# Remove all acknowledgements from database
```python
from alerts.models import AlertAcknowledgementHistory
AlertAcknowledgementHistory.objects.all().delete()
```

# query on database
```python
from alerts.models import AlertGroup, AlertInstance
import json
from django.core.serializers.json import DjangoJSONEncoder

alert_group = AlertGroup.objects.filter(
name='NodeExporterNotScrape16',
labels__instance='localhost:9100'
).first()
   
if alert_group:
	print(f"Alert Group Found: {alert_group.name} (ID: {alert_group.id})")
	print(f"Fingerprint: {alert_group.fingerprint}")
	print(f"Status: {alert_group.current_status}")
	print(f"Severity: {alert_group.severity}")
	print(f"Total Firing Count: {alert_group.total_firing_count}")
	print(f"First Occurrence: {alert_group.first_occurrence}")
	print(f"Last Occurrence: {alert_group.last_occurrence}")
	print(f"Acknowledged: {alert_group.acknowledged}")
   
   
instances = AlertInstance.objects.filter(alert_group=alert_group).order_by('started_at')
print(f"\nTotal Instances: {instances.count()}")
   
for i, instance in enumerate(instances, 1):
	print(f"\n{i}. Status: {instance.status}")
	print(f"   Started: {instance.started_at}")
	print(f"   Ended: {instance.ended_at or 'Still Active'}")
	annotations = json.dumps(instance.annotations, indent=2, cls=DjangoJSONEncoder)
	print(f"   Annotations: {annotations}")
	print(f"   ID: {instance.id}")
```


# Remove silence 
```python
from alerts.models import SilenceRule
all_rules = SilenceRule.objects.all()
count = all_rules.count()
print(f"Found {count} SilenceRule object(s) to delete.")
if count > 0:
    # This is the command that actually deletes the records
    deletion_result = all_rules.delete()
    print(f"Deletion complete. Result: {deletion_result}")
    print(f"Successfully deleted {deletion_result[0]} SilenceRule object(s).")
else:
    print("No SilenceRule objects found to delete.")
```

# Remove silence from alert
```python
from alerts.models import AlertGroup
alerts_to_unsilence = AlertGroup.objects.filter(is_silenced=True)
count = alerts_to_unsilence.count()
print(f"Found {count} AlertGroup object(s) currently marked as silenced.")
if count > 0:
    print("Updating 'is_silenced' to False and 'silenced_until' to None for these alerts...")
    num_updated = alerts_to_unsilence.update(is_silenced=False, silenced_until=None)
    print(f"Successfully updated {num_updated} AlertGroup record(s).")
else:
    print("No silenced AlertGroup objects found to update.")
```

# Tasks 
1. ~~move /alerts/alerts to /alerts~~
2. ~~upload code to github~~


# Production 
export PYTHONPATH=/etc/sentryhub
python3 manage.py shell --settings=settings
python3 manage.py collectstatic --settings=settings