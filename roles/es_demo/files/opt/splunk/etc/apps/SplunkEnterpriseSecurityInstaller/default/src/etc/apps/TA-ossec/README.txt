OSSEC Add-on README
==============================
Author: Splunk
Author contact info:
Version:1.0
Date this version was posted to Splunkbase:
Supported product(s): OSSEC 2.7
Supported platforms(s): *nix , Windows
	

Overview
---------
This Add-on can import data directly by monitoring logs on the OSSEC Manager Server via syslog.	

* Sourcetype : ossec

* Input defined : OSSEC has its inbuilt features to send data over UDP to Splunk. The data must be sent to Splunk over  UDP port 514 through syslog.

* Configuration: Automatic

* Ports for automatic configuration: 514 (UDP)

* Scripted input setup: Not applicable

* Index-time operations: false, this TA need not to be deployed on indexers.

* Lookups defined :			                
                   
Following lookup files were used to map the fields in compliance with Enterprise Security:
	
1. "ossec_vendor_info.csv" is a look-up file in 'lookups' folder, it contains information about Vendor, Product and ids_type.

2. "ossec_severities.csv" is a look-up file in 'lookups' folder, it maps severity_ids to their corresponding severities in compliance with the Common information model.
	
Please don't modify the above csv files, else you may not see the correct results in Enterprise Security dashboards.                  
   
Where to deploy this add-on
---------------------------
This add-on is deployed using search-heads.
                
Using this Add-on:
-----------------------------

 This Add-on can import data directly by monitoring logs on the OSSEC Manager Server via syslog. To monitor the logs directly you'll need to set the UDP input type in the props.conf file and enable the associated inputs. To do so:
     Uncomment and modify the stanza ([source::udp:514]) below based on incoming OSSEC data
       #[source::udp:514]
       #TRANSFORMS-force_sourcetype_for_ossec_syslog = force_sourcetype_for_ossec

Configuration steps:	
--------------------
                    
	This plug-in is configured to listen to UDP port 514 to receive syslog data from OSSEC Manager. So OSSEC Manager must be configured to send log information over UDP port 514
	
	To Configure OSSEC Manager to send log data to splunk:

		1.Inside ossec.conf add a syslog_output block specifying your Splunk system IP address and the port it is listening on:
 
			<syslog_output>
 
			<server>172.10.2.3</server>
 
			<port>514</port>
 
			</syslog_output>
 
		2.Now enable the syslog_output module and restart OSSEC:
 
			#/var/ossec/bin/ossec-control enable client-syslog
 
			#/var/ossec/bin/ossec-control restart

               
					 
	Copyright (C) 2009-2013 Splunk Inc. All Rights Reserved.
