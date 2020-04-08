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

log = logging.getLogger(__name__)

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
    all_instances = []
    active_instances = []
    config_repo = None
    instance_id = None

    # Go through the data line by line and search for id,repo and routes
    # and append them in active_instances
    for line in data_split:

        line = line.strip()
        # All the instance_ids start with '=='
        if line.startswith('== '):
            if instance_id:
                if config_repo != 'null':
                    repo = 'https://{}'.format(config_repo.group(1))
                else:
                    repo = 'null'
                all_instances.append({
                        'id': instance_id.group(1),
                        'config_repo':repo,
                        'instance_url':url_list
                        })
                config_repo = 'null'
                url_list = []
            
            instance_id = re.search('== (.*)', line)
            instance = instance_id.group(1)
        
        # Lines starting with 'image' contain the config_repo
        if line.startswith('image'):
            config_repo = (re.search('imageFromGitlab: (.*)',line) or
            re.search('registry.(.*)', line))
            if (re.search('registry.(.*)@', line)):
                config_repo = re.search('registry.(.*)@', line)
        
        # Lines starting with '-' contain the url_routes
        if line.startswith('-'):
            url = re.search('- (.*)', line)
            route = 'https://{}'.format(url.group(1))
            url_list.append(route)
    
    # To get the last entry of the instance list
    all_instances.append({
                        'id': instance,
                        'config_repo':repo,
                        'instance_url':url_list
                         })
    
    # Remove instances that don't have any active route
    for instances in all_instances:
        if instances['instance_url']:
            active_instances.append(instances)
    
    return active_instances

@toolkit.side_effect_free
def update_instance_list(context, data_dict):
    '''Writes the list of instances to a googlesheet
    https://docs.google.com/spreadsheets/d/{sheet_key}/{worksheet_id}
    Also adds a csv of the active instances to a dataset of the running instance
    '''

    if authz.is_sysadmin(toolkit.c.user):
        active_instances_obs = active_instances(context, data_dict)

        sheet.clear()
        write_row = []
        data_list = []
        prev_count = 0
        
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

        header = ['Instance ID','Config Repository'] + [u'Website URL {0}'.format(i) for i in range(1,prev_count+1)]
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
    
        try:
            result = toolkit.get_action('package_show')(context, {'id': dataset_id})

        except(not_found_error):
            result = toolkit.get_action('package_create')(context, 
            {'name': dataset_id,'owner_org': owner_org_id })

        # If the resource is not found in the dataset create one
        if not any(d['name'] == resource_name for d in result['resources']):
            #logging.info('Created new resource')
            upload_file(csv_file, u'create', None)
        
        # Update existing resource    
        else:
            for resource in result['resources']:
                if resource['name'] == resource_name:
                    resource_id = resource['id']
                    break
            upload_file(csv_file, u'update',resource_id)
        
            #logging.info('Updating the resource')

    user_list = ckan.logic.get_action('user_list')(context, data_dict)
    user_name_list = [user['name'] for user in user_list]
    if toolkit.c.user not in user_name_list:
        toolkit.abort(403, _('You are not authorized to access this list'))

    return u'https://docs.google.com/spreadsheets/d/{}/edit#gid={}'.format(sheet_key, worksheet_id)

def create_dataset_csv(active_instances_obs):
    
    maxList = max(active_instances_obs, key = lambda i: len(i)) 
    maxLength = len(maxList)
    
    csv_columns = ['Instance ID','Config Repository'] + ['Website URL {0}'.format(i) for i in range(1,maxLength-1)]
    #csv_file = '{}/{}'.format(config.get('ckan.storage_path'),'upload.csv')
    csv_file = '{0}/{1}'.format('/srv/app/','upload.csv')

    try:
        with open(csv_file, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(active_instances_obs)

    except IOError:
        print("I/O error")
        #logging.error("I/O error")
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
            else:
                toolkit.get_action('resource_update')(context, 
                {'id':resource_id,'upload':upload})
