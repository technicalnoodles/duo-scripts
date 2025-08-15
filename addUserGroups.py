import csv
import json
import duo_client

groups = {
    'hr':[{'hrms_write': 'group_id_here'}, {'saleforce_read':'group_id_here'}],
    'it':[{'palo_alto_admins': 'group_id_here'},{'saleforce_write': 'group_id_here'}],
}
 

admin_api = duo_client.Admin(
    ikey='',
    skey='',
    host='')

users = admin_api.get_users()
duo_user_output = users

for user in duo_user_output:
    if user['status'] == 'disabled':
        continue
    if 'hr' in user['custom_attributes']['Department'].lower():
        for group in groups['hr']:
            for i in list(group.keys()):
                group_id = group[i]
                if(group_id in str(user['groups'])):
                    continue
                response = admin_api.json_api_call(
                    'POST',
                    '/admin/v1/users/' + user['user_id'] + '/groups',
                    {"group_id": group_id}
                )  
                print(response)
    if 'it' in user['custom_attributes']['Department'].lower():
        for group in groups['it']:
            for i in list(group.keys()):
                group_id = group[i]
                if(group_id in str(user['groups'])):
                    continue
                response = admin_api.json_api_call(
                    'POST',
                    '/admin/v1/users/' + user['user_id'] + '/groups',
                    {"group_id": group_id}
                )  
                print(response)
