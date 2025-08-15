import csv
import json
import duo_client
import sys
import io
import requests
import emails
from emails.template import JinjaTemplate as T
from bs4 import BeautifulSoup

SSO_ENROLLMENT="enrollment link here"
APP_PORTAL = "duo central link here"
EMAIL_SERVER = "email server here"
EMAIL_PORT = 25
EMAIL_SSL = False

# Configuration and information about objects to create.
admin_api = duo_client.Admin(
    ikey='',
    skey='',
    host='')

input_csv = """
Email Address,First Name,Last Name,Company Name,Phone Number
email@email.com,Blah,Blargh,Fancy Company,5555555555
"""
output_json = "crew_output.json"

null = None
true = True
false = False

users = admin_api.get_users()
duo_user_output = users


csvfile = io.StringIO(input_csv.strip())
reader = csv.DictReader(csvfile)
results = []
for row in reader:
    first_name = row['First Name'].strip()  # preserve original casing
    last_name = row['Last Name'].strip()  # preserve original casing
    company = row['Company Name'].strip()
    email_address = row['Email Address'].strip()
    results.append({
        'first_name': first_name,
        'last_name': last_name,
        'custom_attributes.Company': company,
        'custom_attributes.external-email': email_address
    })

# Step 2: Compare CSV users to Duo users and check for 'Disabled' group
users_needing_enable = []

for csv_user in results:
    csv_first = csv_user['first_name']
    csv_last = csv_user['last_name']
    for duo_user in duo_user_output:
        duo_first = (duo_user.get('firstname') or '').strip().lower()
        duo_last = (duo_user.get('lastname') or '').strip().lower()
        # Also try matching 'benjamin' as 'ben'
        csv_first_alt = 'ben' if csv_first == 'benjamin' else csv_first
        if (csv_first == duo_first or csv_first_alt == duo_first) and csv_last == duo_last:
            # Check if user is in a group named 'Disabled'
            groups = duo_user.get('groups', [])
            if any((group.get('name') or '').lower() == 'disabled' for group in groups):
                users_needing_enable.append({
                    'email': duo_user.get('email', ''),
                    'user_id': duo_user.get('user_id', '')
                })

# Output the list to a new JSON file
print("\nUsers needing to be enabled (count: {}):".format(len(users_needing_enable)))
print(json.dumps(users_needing_enable, ensure_ascii=False, indent=2))

# Step 3: Find users in CSV not present in Duo data
users_not_in_duo = []
for csv_user in results:
    csv_first_orig = csv_user['first_name']
    csv_last_orig = csv_user['last_name']
    csv_first = csv_first_orig.strip().lower()
    csv_last = csv_last_orig.strip().lower()
    csv_first_alt = 'ben' if csv_first == 'benjamin' else csv_first
    found = False
    for duo_user in duo_user_output:
        duo_first = (duo_user.get('firstname') or '').strip().lower()
        duo_last = (duo_user.get('lastname') or '').strip().lower()
        if (csv_first == duo_first or csv_first_alt == duo_first) and csv_last == duo_last:
            found = True
            break
    # Ignore certain users based on first and last names
    ignore_black_hat = [
        ("john", "snow"),
        ("james", "snow")
    ]
    company = csv_user['custom_attributes.Company'].strip().lower()
    skip = False
    #change this to your management company name if there are certain groups of users you want to skip
    if company == "management company":
        for fname, lname in ignore_black_hat:
            if csv_first == fname and (csv_last == lname or lname == ""):
                skip = True
                break
    if not found and not skip:
        users_not_in_duo.append(csv_user)

print("\nUsers in CSV not found in Duo (count: {}):".format(len(users_not_in_duo)))

# Add guessed email addresses
users_not_in_duo_with_emails = []
for user in users_not_in_duo:
    # Preserve original casing in output, only lowercase for email
    first_orig = user['first_name']
    last_orig = user['last_name']
    first = first_orig.strip().lower()
    last = last_orig.replace(' ', '').strip().lower()
    email_guess = f"{first}.{last}@change_to_your_domain"
    user_with_email = dict(user)
    user_with_email['email'] = email_guess
    user_with_email['username'] = email_guess.replace('@change_to_your_domain', '')
    # Use 'firstname' and 'lastname' in output
    user_with_email['firstname'] = first_orig
    user_with_email['lastname'] = last_orig
    user_with_email['realname'] = f"{first_orig} {last_orig}"
    # Preserve original CSV email for later use
    user_with_email['custom_attributes.external-email'] = user['custom_attributes.external-email']
    # Remove old keys if present
    user_with_email.pop('first_name', None)
    user_with_email.pop('last_name', None)
    user_with_email.pop('email_guess', None)
    users_not_in_duo_with_emails.append(user_with_email)

print("\nUsers not in Duo with guessed emails (count: {}):".format(len(users_not_in_duo_with_emails)))
print(json.dumps(users_not_in_duo_with_emails, ensure_ascii=False, indent=2))

# Return the list for use in other applications
users_not_in_duo_with_emails
user_ids_with_email = []
new_users_in_duo = []
for new_user in users_not_in_duo_with_emails:
    email = new_user['email']
    new_user['email'] = new_user['custom_attributes.external-email']
    new_user['custom_attributes.external-email'] = email
    print("\nCreating user:")
    print(new_user)
    response = admin_api.json_api_call(
        'POST',
        '/admin/v1/users',
        new_user
    )   
    user_ids_with_email.append({'user_id':response['user_id'], 'email': new_user['email'], 'external_email': new_user['custom_attributes.external-email']})
    new_users_in_duo.append(response)
    print(response)

print(new_users_in_duo) 

# Create mapping from username to CSV email address
username_to_external_email = {}
for user_data in users_not_in_duo_with_emails:
    username_to_external_email[user_data['username']] = user_data['custom_attributes.external-email']

enrollment_info_list = []
for user in new_users_in_duo:
    enrollment_code = admin_api.json_api_call(
        'POST',
        '/admin/v1/users/enroll',
        {
            'username': user['username'],
            'email': user['email'],
            'valid_secs': '518400'
        }
    )

    change_email = admin_api.json_api_call(
        'POST',
        '/admin/v1/users/' + user['user_id'],
        {
            'email': user['custom_attributes']['external-email'],
            'custom_attributes.external-email': user['email']
        }
    )
    # Get CSV email address for this user
    external_email = username_to_external_email.get(user['username'], user['email'])
    
    enrollment_info = {
        'enrollment_code': enrollment_code,
        'email': user['email'],
        'username': user['username'],
        'send_to_email': external_email,
        'enrollment_url': SSO_ENROLLMENT,
        'portal_url': APP_PORTAL
    }
    enrollment_info_list.append(enrollment_info)


print(json.dumps(enrollment_info_list, ensure_ascii=False, indent=2))


def email_customer(email, username, email_to):
    SMTP_SERVER = EMAIL_SERVER
    SMTP_PORT = EMAIL_PORT
    SMTP_SSL = EMAIL_SSL

    email_template = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"></head>
<body>
    <div style="max-width:800px">
        <p>Welcome to your_company_here,</p>
        <p></p>
        <p>Insert welcome info here</p>
        <p>Email: {email}</p>
        <p>Username: {username}</p>
        <p></p>
        <p>After you have enrolled, you can go to the below link to access your applications.</p>
        <p>Portal URL: app_portal_link</p>
        <p></p>
        <p>If you have any questions, please contact _admin_here or respond to this message</p>
        <p></p>
        <p>Best regards,</p>
        <p>yourself_here</p>
    </div>
</body>
</html>
    """.format(email=email_to, username=username)

    message = emails.Message(
        html=T(email_template),
        # text=T(email_text_template),
        mail_from=("Name_of_sender", "sender_email"),
        subject="title_of_email_here",
    )

    render = {
        "email_body": email_template,
        "email_body_text": BeautifulSoup(email_template, "lxml").get_text(),
    }

    r = message.send(
        to=email,
        render=render,
        smtp={"host": SMTP_SERVER, "port": SMTP_PORT, "ssl": SMTP_SSL},
    )

    return r

# Loop through enrollment info list
for enrollment_info in enrollment_info_list:
    email_customer(enrollment_info['email'], enrollment_info['username'], enrollment_info['send_to_email'])
   