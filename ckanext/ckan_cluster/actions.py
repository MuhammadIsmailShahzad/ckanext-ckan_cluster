import ckan.plugins as plugins
from ckan import authz
from pylons import config
import ckan.plugins.toolkit as toolkit
from ckan.common import _ 
import ckan.logic
import ckan.logic.action
import jenkins
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import logging
import time

user = config.get('ckan.jenkins_user')
server_port = config.get('ckan.jenkins_server_port')
jenkins_key = config.get('ckan.jenkins_token')

# use creds to create a client to interact with the Google Drive API 
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

creds = ServiceAccountCredentials.from_json_keyfile_name('/srv/app/client_secret.json', scope)
client = gspread.authorize(creds)
sheet_key = config.get('ckan.gsheet_id')
worksheet_id = config.get('ckan.gsheet_worksheet')
sheet_name = config.get('ckan.gsheet_name')
gsheet = client.open_by_key(sheet_key)
sheet = gsheet.get_worksheet(int(worksheet_id))


@toolkit.side_effect_free
def active_instances(context, data_dict):
    '''Returns a list of active instances of ckan'''

    if not authz.is_sysadmin(toolkit.c.user):
        toolkit.abort(403, _('You are not authorized to access this list'))
    
    server = jenkins.Jenkins(server_port, username=user, 
                         password=jenkins_key)
    job_name = 'simplified list instances' 

    # Get the console output of the latest build of the job 
    info = server.get_job_info(job_name)
    builds = info['builds']
    number = int(builds[-1]['number'])
    console_output = server.get_build_console_output(job_name, number)
    
    data_split = console_output.split('\n')
    
    url_list = []
    active_instances = []

    # Go through the data line by line and search for id,repo and routes
    # and append them in active_instances
    for line in data_split:
        line = line.strip()  
        instance_id = re.search('== (.*)', line)
        git_repo = (re.search('registry.(.*)@', line) or
        re.search('imageFromGitlab: (.*)',line))
        url = None

        if line.startswith('-'):
            url = re.search('- (.*)', line)

        if instance_id:
            instance_rep = instance_id.group(1)       
            if url_list:
                active_instances.append({
                    'id': instance_id_data,
                    'config_repo':repo, 
                    'instance_url':url_list
                     })
                url_list = []
        if git_repo:
            repo = 'https://'+ git_repo.group(1)
        if url:
            route = 'https://'+ url.group(1)
            url_list.append(route)
            instance_id_data = instance_rep
    
    active_instances.append(
        {
            'id':instance_id_data,
            'config_repo':repo,
            'instance_url':url_list
        }
    )
    return active_instances
    
@toolkit.side_effect_free
def update_gsheet(context, data_dict):
    '''Writes the list of instances to a googlesheet 
    https://docs.google.com/spreadsheets/d/{sheet_key}/{worksheet_id}'''
    
    if authz.is_sysadmin(toolkit.c.user):
        active_instances_obs = active_instances(context, data_dict) 
    
        sheet.clear()
        header = ['id','config_repo','url_routes']
        write_row = []
        new_list = []
        new_list.append(header)

        for x in active_instances_obs:
            write_row.append(str(x['id']))
            write_row.append(str(x['config_repo']))
            write_row.append(str(x['instance_url']).replace('u\'',' ').replace('\'',''))
            new_list.append(write_row)
            write_row = []

        gsheet.values_update(
            sheet_name+'!A1',
            params={
                'valueInputOption': 'USER_ENTERED'
            },
            body={
                'values': new_list
            }
        )
    user_list = ckan.logic.get_action('user_list')(context, data_dict)
    
    user_name_list = []
    for user in user_list:
        user_name_list.append(user['name'])
    
    if toolkit.c.user not in user_name_list:
        toolkit.abort(403, _('You are not authorized to access this list'))

    return u'https://docs.google.com/spreadsheets/d/{}/edit#gid={}'.format(sheet_key, worksheet_id)