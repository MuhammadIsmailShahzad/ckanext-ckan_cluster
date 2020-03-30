import ckan.plugins as plugins
from ckan import authz
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
import csv
from ckan.common import config
import cgi


user = config.get('ckan.jenkins_user')
server_port = config.get('ckan.jenkins_server_port')
jenkins_key = config.get('ckan.jenkins_token')
not_found_error = ckan.logic.NotFound

# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

creds = ServiceAccountCredentials.from_json_keyfile_name('/srv/app/client_secret.json', scope)
client = gspread.authorize(creds)
sheet_key = config.get('ckan.gsheet_id')
worksheet_id = config.get('ckan.gsheet_worksheet')
sheet_name = config.get('ckan.gsheet_name')
dataset_id = config.get('ckan.dataset_id')
owner_org_id = config.get('ckan.owner_org_id')
resource_name = config.get('ckan.resource_name')
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
    number = int(builds[0]['number'])
    console_output = server.get_build_console_output(job_name, number)

    data_split = console_output.split('\n')

    url_list = []
    active_instances = []

    # Go through the data line by line and search for id,repo and routes
    # and append them in active_instances
    for line in data_split:
        line = line.strip()
        instance_id = re.search('== (.*)', line)
        git_repo = (re.search('imageFromGitlab: (.*)',line) or
        re.search('registry.(.*)', line))

        if (re.search('registry.(.*)@', line)):
            git_repo = re.search('registry.(.*)@', line)

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
            repo = 'https://{}'.format(git_repo.group(1))
        if url:
            route = 'https://{}'.format(url.group(1))
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
        write_row = []
        data_list = []
        prev_count = 0
        
        max_instances_list = max(active_instances_obs, key = lambda i: len(i)) 
        max_routes_length = len(max_instances_list)
    
        for x in active_instances_obs:

            write_row.append(str(x['id']))
            write_row.append(str(x['config_repo']))

            count = 0

            for url in x['instance_url']:

                write_row.append(str(url))
                count += 1

                if count > prev_count:
                    prev_count = count

            data_list.append(write_row)
            write_row = []

        header = ['id','config_repo'] + [u'route no. {0}'.format(i) for i in range(1,prev_count+1)]
        data_list.insert(0,header)

        gsheet.values_update(
            sheet_name+'!A1',
            params={
                'valueInputOption': 'USER_ENTERED'
            },
            body={
                'values': data_list
            }
        )
    
    csv_file = create_dataset_csv(data_list)
    
    user_list = ckan.logic.get_action('user_list')(context, data_dict)
    user_name_list = [user['name'] for user in user_list]

    if toolkit.c.user not in user_name_list:
        toolkit.abort(403, _('You are not authorized to access this list'))

    try:
        result = toolkit.get_action('package_show')(context, {'id': dataset_id})

    except(not_found_error):
        result = toolkit.get_action('package_create')(context, 
        {'name': dataset_id,'owner_org': owner_org_id })
        logging.error('EXCEPT')

    # If the resource is not found in the dataset create one
    if not any(d['name'] == resource_name for d in result['resources']):
        logging.info('Created new resource')
        upload_file(csv_file, u'create', None)
        
    # Update existing resource    
    else:
        for resource in result['resources']:
            if resource['name'] == resource_name:
                resource_id = resource['id']
                break
        logging.error('Please update {}'.format(resource_id))
        upload_file(csv_file, u'update',resource_id)
        
        logging.info('Updating the resource')
    
    return u'https://docs.google.com/spreadsheets/d/{}/edit#gid={}'.format(sheet_key, worksheet_id)

def create_dataset_csv(active_instances_obs):
    
    maxList = max(active_instances_obs, key = lambda i: len(i)) 
    maxLength = len(maxList)
    
    csv_columns = ['id','config_repo'] + ['route no. {0}'.format(i) for i in range(1,maxLength-1)]
    csv_file = '{}/{}'.format(config.get('ckan.storage_path'),'upload.csv')

    try:
        with open(csv_file, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(active_instances_obs)

    except IOError:
        print("I/O error")
    return csv_file

def upload_file(csv_file, action, resource_id):
       context = {
           'ignore_auth': True,
           'user': '',
       }
       with open(csv_file, 'rb') as csv_file:
            upload = cgi.FieldStorage()
            upload.filename = getattr(csv_file, 'name', 'data')
            upload.file = csv_file
            if action == u'create': 
                toolkit.get_action('resource_create')(context, 
                {'package_id':dataset_id,'url':'active instances', 
                'upload': upload,'name':'active_instances.csv'})
                logging.error('CREATE')
            else:
                toolkit.get_action('resource_update')(context, 
                {'id':resource_id,'upload':upload})
                logging.error('UPDATE')
