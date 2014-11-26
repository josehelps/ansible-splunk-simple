Universal Forwarder
========
Builds a forwarder using the binary file specified in group\_vars/all.yml or the universal\_forwarder.yml playbook to be specific. 

Role Variables
--------------
Check group\_vars/all.yml or universal\_forwarder.yml to be more specific for splunk variables


Notes
--------------
Need to add aplay to install apps


Example Playbook
-------------------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: servers
      roles:
         - { role: username.rolename, x: 42 }

