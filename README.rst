.. You should enable this project on travis-ci.org and coveralls.io to make
   these badges work. The necessary Travis and Coverage config files have been
   generated for you.

.. image:: https://travis-ci.org/ckan/ckanext-ckan_cluster.svg?branch=master
    :target: https://travis-ci.org/ckan/ckanext-ckan_cluster

.. image:: https://coveralls.io/repos/ckan/ckanext-ckan_cluster/badge.svg
  :target: https://coveralls.io/r/ckan/ckanext-ckan_cluster

.. image:: https://pypip.in/download/ckanext-ckan_cluster/badge.svg
    :target: https://pypi.python.org/pypi//ckanext-ckan_cluster/
    :alt: Downloads

.. image:: https://pypip.in/version/ckanext-ckan_cluster/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-ckan_cluster/
    :alt: Latest Version

.. image:: https://pypip.in/py_versions/ckanext-ckan_cluster/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-ckan_cluster/
    :alt: Supported Python versions

.. image:: https://pypip.in/status/ckanext-ckan_cluster/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-ckan_cluster/
    :alt: Development Status

.. image:: https://pypip.in/license/ckanext-ckan_cluster/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-ckan_cluster/
    :alt: License

=============
ckanext-ckan_cluster
=============

This extension fetches the list of active instances along with their config-repos and routes
from jenkins and writes the data to a csv which is then pushed as a resource to a dataset.

* It has two two action endpoints
    * /api/actions/active_instances
        * Returns a list of active instances along with their config-repo and url-routes
    * /api/actions/update_instance_list
        * Writes the active-instances to gsheet
        * Looks for an organization with organization_name(configurable)
        * If not present prompts with a message that organization not found
        * If present creates a dataset with dataset_name(configurable) if already not present
        * Adds a resource to it if not already present and updates the resource if its already there

------------
Requirements
------------

* The extension has following requirements
    * python-jenkins==1.6.0
    * gspread==3.2.0
    * oauth2client==4.1.3

------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-ckan_cluster:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-ckan_cluster Python package into your virtual environment::

     pip install ckanext-ckan_cluster

3. Add ``ckan_cluster`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config Settings
---------------

Following config settigs should be set up while running the extension

* Jenkins setup
    * Set followind config settings for jenkins::   
      
        # The endpoint you are using for your jenkins server
        ckan.jenkins_server_port = some_url 
        # API Token in the configure setting of your jenkins account 
        ckan.jenkins_token = some_token_value
        # The email you use for jenkins
        ckan.jenkins_user = some_email
* Org and Dataset name
    * Set organization name and dataset name by using these variables:: 
      
        # The organization you want to be used for uploading the dataset
        ckan.owner_org_id = operations
        # The name you want the resource to have when its created
        ckan.dataset_id = list-instances-dataset
        # The name you want the resource to have when its uploaded
        ckan.resource_name = active_instances.csv
* Google Sheets Setup
    * Go to the site https://console.developers.google.com/
    *  Login to your google account.
    * Create new project and enable Google Sheets API and Google Drive API.
    * Get the credentials.json file.
    * Rename the credential.json file to `client_secret.json` and COPY it to `/srv/app/client_secret.json` in the Dockerfile 
    * Set following config settings::  
          
        # The id of the sheet you want to update
        ckan.gsheet_id = some_id
        # Worksheet id eg 0
        ckan.gsheet_worksheet = 0
        # Sheet name eg Sheet1
        ckan.gsheet_name = Sheet1


------------------------
Development Installation
------------------------

To install ckanext-ckan_cluster for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/ckan/ckanext-ckan_cluster.git
    cd ckanext-ckan_cluster
    python setup.py develop
    pip install -r dev-requirements.txt


-----------------
Running the Tests
-----------------

To run the tests, do::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.ckan_cluster --cover-inclusive --cover-erase --cover-tests


---------------------------------
Registering ckanext-ckan_cluster on PyPI
---------------------------------

ckanext-ckan_cluster should be availabe on PyPI as
https://pypi.python.org/pypi/ckanext-ckan_cluster. If that link doesn't work, then
you can register the project on PyPI for the first time by following these
steps:

1. Create a source distribution of the project::

     python setup.py sdist

2. Register the project::

     python setup.py register

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the first release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do::

       git tag 0.0.1
       git push --tags


----------------------------------------
Releasing a New Version of ckanext-ckan_cluster
----------------------------------------

ckanext-ckan_cluster is availabe on PyPI as https://pypi.python.org/pypi/ckanext-ckan_cluster.
To publish a new version to PyPI follow these steps:

1. Update the version number in the ``setup.py`` file.
   See `PEP 440 <http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers>`_
   for how to choose version numbers.

2. Create a source distribution of the new version::

     python setup.py sdist

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.2 then do::

       git tag 0.0.2
       git push --tags
