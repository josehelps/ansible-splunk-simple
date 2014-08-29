======================================================================
Splunk Add-on for OSSEC
======================================================================
Author:                  Splunk, Inc.
Add-on Name:             Splunk Add-on for OSSEC
Add-on Version:          1.0.0
Add-on Date:             07.31.13

Vendor Product(s):       OSSEC 2.7
Vendor Platform(s):      *nix , Windows
Splunk Platform(s):      4.x.x, 5.x.x
Splunk CIM Compatible:   Yes

Description
------------------------------
The Splunk Add-on for OSSEC allows a Splunk administrator to collect and ingest OSSEC alert log data in both default and Splunk formats. Once ingested, the alert logs can be analyzed directly or used as a contextual data feed to correlate with other security data in Splunk. This add-on provides the inputs and CIM-compatible knowledge to use the add-on with other Splunk apps, such as Splunk App for Enterprise Security and Splunk App for PCI Compliance.

Data Types
------------------------------
This add-on provides the index-time and search-time knowledge for the following types of data from OSSEC:

1. Alert log: This log file contains the OSSEC HIDS alerts logs which are generated after analysis by OSSEC. OSSEC can be configured to push the alerts through syslog in both default and splunk format via UDP. This Add-on supports both the formats.

  - Sourcetype: ossec 

To Configure OSSEC Manager to send log data to splunk
========================================================

    1. Inside ossec.conf add a syslog_output block specifying your Splunk server IP address and the port it is listening on:
     Ex.
        <syslog_output>
 
        <server>172.10.2.3</server> ##syslog server IP
 
        <port>514</port>  ##default
    
        <format> splunk </format>  ##For Splunk format
 
        </syslog_output>
 
    2.Now enable the syslog_output module and restart OSSEC using the following commands:
 
        #/var/ossec/bin/ossec-control enable client-syslog
 
        #/var/ossec/bin/ossec-control restart

Installation and Configuration
-------------------------------
Installation of the add-on to the search head
=============================================

The add-on needs to be installed to the search head to allow a user to use the search-time knowledge provided within the add-on. To install the add-on, do the following:

1. Download the app from Splunkbase (Already done if you are reading this).
2. From the Splunk web interface, click on App -> Manage Apps to open the Apps Management page in Manager.
3. Click the "Install app from file" button, locate the downloaded file and click "Upload".
4. Verify (if necessary) that the app is installed.  It should be listed in the list of apps installed within the Manager and can be found on the server at $SPLUNK_HOME/etc/apps/TA-ossec.

Installation of the add-on to the indexers
=============================================

If your Splunk deployment consists of a single server, you don't need to follow this step. If your deployment is distributed, you may need to follow this step, but only if you expect to sourcetype the OSSEC data on the indexer instead of via a Splunk Forwarder.

Note: This step will require a restart of the indexer(s).

To install the app to the indexers, do the following:

1. Upload the TA-ossec folder to the indexer and put into the $SPLUNK_HOME/etc/apps directory.
2. Restart the indexer.

Data received by the indexer that matches the sourcetype rules in the props.conf and transforms.conf file will automatically be sourcetyped.
If the file name of the alert log file is changed the props / transforms defined may need to be updated to reflect the new file format.

Add-on Lookups
------------------------------

1. OSSEC Severity lookup - translates severity_id to severity for this add-on. 

   - File location: $SPLUNK_HOME/TA-ossec/lookups/ossec_severities_lookup.csv
   - Lookup fields: severity_id,severity
   - Lookup contents:
         11,medium
         12,high

2. OSSEC Endpoint Change action lookup - translates status to action for this add-on.

   - File location: $SPLUNK_HOME/TA-ossec/lookups/ossec_change_action_lookup.csv.
   - Lookup fields: change_type,action,status
   - Lookup contents: 
         Integrity checksum changed.,modified,success
         Integrity checksum changed again (2nd time).,modified,success

3. Vendor product lookup - defines the vendor and product for this add-on.

   - File location: $SPLUNK_HOME/TA-ossec/lookups/ossec_vendor_lookup.csv
   - Lookup fields: sourcetype,vendor,product,ids_type
   - Lookup contents:
         ossec,"Open Source Security",HIDS,host

Copyright (C) 2009-2013 Splunk Inc. All Rights Reserved.