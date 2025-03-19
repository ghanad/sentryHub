# Alert Acknowledgement Feature

This document describes the alert acknowledgement feature implementation in the SentryHub alert management system.

## Overview

The alert acknowledgement feature allows operators to acknowledge alerts with a mandatory comment. This ensures that team members can understand why an alert was acknowledged and what actions were taken.

## Features

1. **Mandatory Comments**: 
   - Users must provide a comment when acknowledging an alert
   - Comments explain the reason for acknowledgement or describe actions being taken

2. **User Interface**:
   - Modal dialog for acknowledging alerts with comment field
   - Form validation to ensure comment is provided
   - Success/error messages for user feedback

3. **API Support**:
   - REST API support for acknowledging alerts
   - Comment field required in API requests

## How It Works

### Web Interface

1. User clicks "Acknowledge" button on an alert
2. A modal dialog appears requesting a comment
3. User enters comment and submits form
4. Alert is acknowledged and comment is saved
5. Alert detail page shows acknowledgement status, user, time, and comment

### API

API clients must include a comment when acknowledging alerts:

```json
{
  "acknowledged": true,
  "comment": "Restarting the service to address high CPU usage"
}
```

## Database Changes

- The `AlertComment` model stores acknowledgement comments
- The `AlertGroup` model tracks acknowledgement status, user, and time

## Security

- Only authenticated users can acknowledge alerts
- User who acknowledges an alert is recorded in the database

## Usage Scenarios

1. **Incident Response**:
   - Operator acknowledges critical alert
   - Comment explains immediate actions taken
   - Other team members can see who is handling the incident

2. **False Positive Handling**:
   - Operator acknowledges warning alert
   - Comment explains why alert is a false positive
   - Can reference ticket for permanent resolution

3. **Routine Maintenance**:
   - Operator acknowledges expected alerts during maintenance
   - Comment references maintenance window and expected duration
   - Prevents duplicate work by other team members