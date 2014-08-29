#!/bin/sh
SPLUNK_HOME=/opt/splunk
$SPLUNK_HOME/bin/splunk cmd python $SPLUNK_HOME/etc/apps/es_demo/bin/es_demo.py -r >> /var/log/es_demo.log
cp /root/passwd $SPLUNK_HOME/etc
touch $SPLUNK_HOME/etc/.ui_login
$SPLUNK_HOME/bin/splunk restart
