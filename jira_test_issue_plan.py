#!/usr/bin/env python3

from jira import JIRA
import getpass # For securely getting the password/token (optional but recommended)
import sys     # To exit gracefully on error

# --- Jira Connection Details ---
# Replace with your Jira server URL
JIRA_SERVER = 'https://jira.tsetmc.com' 

# Replace with your Jira username
JIRA_USERNAME = 'username'
JIRA_PASSWORD_OR_TOKEN = "password" 

# --- Issue Details ---
PROJECT_KEY = 'SAM' # Example: 'PROJ', 'TEST'

ISSUE_SUMMARY = 'Test issue created via Python with Assignee'
ISSUE_DESCRIPTION = 'This is a test issue description created using a Python script and assigned to a specific user.'
ISSUE_TYPE = 'Incident' # Other examples: 'Bug', 'Story', 'Epic'

# --- Assignee Details ---
# !!! مهم: نام کاربری دقیق (username) فرد مورد نظر در جیرا را جایگزین کنید !!!
ASSIGNEE_USERNAME = 'monitoring' # <--- این قسمت را ویرایش کنید

# --- Connect to Jira ---
print(f"Attempting to connect to {JIRA_SERVER} as {JIRA_USERNAME}...")
try:
    # Connection options (if using self-hosted Jira with invalid SSL, you might need 'verify': False, but use with caution)
    options = {'server': JIRA_SERVER}

    # Create the connection instance using Basic Authentication (username & password/token)
    jira_connection = JIRA(options=options, basic_auth=(JIRA_USERNAME, JIRA_PASSWORD_OR_TOKEN))

    print("Successfully connected to Jira.")

except Exception as e:
    print(f"ERROR: Failed to connect to Jira: {e}")
    # More details might be in e.text or e.status_code for connection errors
    # print(f"Status Code: {getattr(e, 'status_code', 'N/A')}")
    # print(f"Response Text: {getattr(e, 'text', 'N/A')}")
    sys.exit(1) # Exit if connection fails

# --- Create the Issue ---
print(f"Creating issue in project '{PROJECT_KEY}'...")

# Dictionary containing the issue details
issue_dict = {
    'project': {'key': PROJECT_KEY},
    'summary': ISSUE_SUMMARY,
    'description': ISSUE_DESCRIPTION,
    'issuetype': {'name': ISSUE_TYPE},
    # --- اضافه کردن Assignee ---
    'assignee': {'name': ASSIGNEE_USERNAME},
    # --------------------------
    # You can add more fields here as needed, for example:
    # 'priority': {'name': 'High'},
    # 'labels': ['python_created', 'test'],
    # 'components': [{'name': 'Backend'}],
    # If you have required custom fields, add them like:
    # 'customfield_10001': 'Some Value',
}

try:
    # Call the create_issue method
    new_issue = jira_connection.create_issue(fields=issue_dict)
    print(f"Successfully created issue!")
    print(f"New issue key: {new_issue.key}")
    # Get the URL (permalink) to the newly created issue
    print(f"Issue URL: {new_issue.permalink()}")
    # نمایش Assignee (اختیاری)
    if new_issue.fields.assignee:
        print(f"Assigned to: {new_issue.fields.assignee.displayName} ({new_issue.fields.assignee.name})")
    else:
        print("Issue is unassigned.")


except Exception as e:
    print(f"ERROR: Failed to create issue: {e}")
    # Common errors: invalid project key, invalid issue type,
    # missing required fields, insufficient user permissions, invalid assignee username.
    # Check the response for details:
    print(f"Status Code: {getattr(e, 'status_code', 'N/A')}")
    print(f"Response Text: {getattr(e, 'text', 'N/A')}") # <--- متن خطا بسیار مهم است
    sys.exit(1)

# --- Close Connection (Optional - usually handled by the library) ---
# jira_connection.close()
print("Script finished.")