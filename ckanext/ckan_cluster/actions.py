import ckan.plugins as plugins
from ckan import authz
from pylons import config
import ckan.plugins.toolkit as toolkit
from ckan.common import _ 
import jenkins
import re
import logging

user = config.get('ckan.jenkins_user')
server_port = config.get('ckan.jenkins_server_port')
jenkins_key = config.get('ckan.jenkins_token')

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

