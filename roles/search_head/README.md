Splunk Search Head
========
Builds a Splunk search head, using the binary file specified in group\_vars/all.yml

Role Variables
--------------
Check group\_vars/all.yml for splunk variables


Notes
--------------
If you would like to implemented your own roles and authorization there is a playbook under this role called security.yml which built for this. Just make sure you update the respective files under `files/opt/splunk/etc/system/local/`


TODO
--------------
* Move splunk installation from deb to tar.gz src file to make it platform agnostic 
