Indexer
========
Builds a splunk indexer using the binary file specified in group\_vars/all.yml or playbooks/indexers.yml

Role Variables
--------------
Check group\_vars/all.yml for splunk variables or playbooks/indexers.yml


Notes
--------------
If you would like to implemented your own roles and authorization there is a playbook under this role called security.yml which built for this. Just make sure you update the respective files under `files/opt/splunk/etc/system/local/`

Example Playbook
-------------------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: servers
      roles:
         - { role: username.rolename, x: 42 }

