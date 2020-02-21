import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.ckan_cluster import actions


class Ckan_ClusterPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)

    # IConfigurer
    # NEW

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ckan_cluster')

    # IActions
    def get_actions(self):
        '''
        Define custom functions (or ovveride existing ones).
        Availbale via API /api/action/{action-name}
        '''
        return {
            'active_instances': actions.active_instances,
            'update_gsheet':actions.update_gsheet
           }
