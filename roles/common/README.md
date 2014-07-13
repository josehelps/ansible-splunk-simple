Role Name
========
Applies common configuration to all servers like copying pub keys, bash\_profile and installing basic utilities

Role Variables
--------------
Check group\_vars/all.yml for splunk variables

Notes
--------------
Make sure you set an email under `files/cron.daily/clamav` and uncomment the last line `#/usr/bin/mail -s "$CV_SUBJECT" $CV_MAILTO -- -f $CV_MAILFROM < $CV_LOGFILE` to receive end of day anti-virus scanned messages

Example Playbook
-------------------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: servers
      roles:
         - { role: username.rolename, x: 42 }

