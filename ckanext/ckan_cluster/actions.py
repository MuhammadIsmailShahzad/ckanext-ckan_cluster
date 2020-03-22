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

user = config.get('ckan.jenkins_user')
server_port = config.get('ckan.jenkins_server_port')
jenkins_key = config.get('ckan.jenkins_token')


logging.error(config)

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
logging.error('GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG')
logging.error(sheet_name)

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
        #header = ['id','config_repo','url_routes']
        write_row = []
        new_list = []
        prev_count = 0
        #new_list.append(header)

        for x in active_instances_obs:
            
            write_row.append(str(x['id']))
            write_row.append(str(x['config_repo']))

            count = 0
            
            for url in x['instance_url']:
                
                write_row.append(str(url))
                count += 1

                if count > prev_count:
                    prev_count = count

            new_list.append(write_row)
            write_row = []
        
        header = ['id','config_repo'] + [u'route no. {0}'.format(i) for i in range(1,prev_count+1)]
        new_list.insert(0,header)        
        
        gsheet.values_update(
            sheet_name+'!A1',
            params={
                'valueInputOption': 'USER_ENTERED'
            },
            body={
                'values': new_list
            }
        )
    csv_file = create_dataset_csv(active_instances_obs)
    user_list = ckan.logic.get_action('user_list')(context, data_dict)
    
    user_name_list = [user['name'] for user in user_list]

    if toolkit.c.user not in user_name_list:
        toolkit.abort(403, _('You are not authorized to access this list'))
    
    dataset_id = 'list-instances-dataset'
    owner_org_id = 'operations'
    resource_id = 'active-instances.csv'
    dataset_id_2 = 'list-instances-dataset-four'
    dataset_id_5 = 'list-instances-dataset-feive'
    resource_url = 'https://raw.githubusercontent.com/MuhammadIsmailShahzad/telecom-operators-of-the-world/master/telecom-operators.csv'

    not_found_error = ckan.logic.NotFound
     
    try:
        result = toolkit.get_action('package_show')(context, {'id': dataset_id})
    
    except(not_found_error):
    
        result = toolkit.get_action('package_create')(context, {'name': dataset_id,'owner_org': owner_org_id })
    result2 = []      
    if resource_id not in result['resources']:
        #if resource == resource_id:
        #    result2 = resource['name']
        #else:
        result2 = u'Please create a resource'
        result2 = toolkit.get_action('resource_create')(context, {'package_id':dataset_id,'upload': csv_file})
        #break
    
    try:
        result1 = toolkit.get_action('resource_show')(context, {'id': resource_id})
    except:
        result1 = u'sorry'
    #toolkit.get_action('resource_view_create')(context, {'resource_id':resource_id})

    return csv_file


    #return u'https://docs.google.com/spreadsheets/d/{}/edit#gid={}'.format(sheet_key, worksheet_id)

def create_dataset_csv(active_instances_obs):
    csv_columns = ['id','config_repo','instance_url']
    csv_file = '{}/{}'.format(config.get('ckan.storage_path'),'active-instances.csv')
    try:
        with open(csv_file, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for data in active_instances_obs:
                writer.writerow(data)
    except IOError:
        print("I/O error")
    return csv_file 