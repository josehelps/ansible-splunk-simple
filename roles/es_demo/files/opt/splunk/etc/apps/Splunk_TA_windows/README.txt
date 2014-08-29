Windows Add-on 
----------------------------------------
Author: Splunk
Source type(s): MonitorWare, NTSyslog, Snare, WinEventLog, DhcpSrvLog, WMI, WindowsUpdateLog, WinRegistry
Has index-time operations: true, this add-on must be placed on indexers
Input requirements: This add-on supports multiple sources; see the "Use this add-on" section for details.
Supported product(s): 
* Microsoft DHCP server
* Windows event logs (provided by Splunk, MonitorWare, NTSyslog, or Snare)
* Windows Update log
* Windows registry (via the Splunk's change monitoring system)
* Microsoft Internet Authentication Service (IAS)
 
New in this release:
--------------------------
- Added TaskCategory "User Account Management" to the account_management event type. (MSAPP-2233)
- Made changes to support Change Analysis:Audit Changes data model object. (SOLNESS-4993)
- Made changes for Filesystem_Changes data model. (SOLNESS-4743)
- Enhanced Windows Server 2008 time synchronization detection. (MSAPP-1848)
- REGRESSION: Fixed an issue where action field was being destroyed by OUTPUT. (MSAPP-2793)
- Updated to accommodate new Endpoint Change data model. (SPL-50859):
The Windows Add-on (Splunk_TA_windows) was updated to accommodate Common Information Model (CIM) changes to "endpoint change" reporting.  This change applies to the "fs_notification" and "WinRegistry" source types.
The specific field names and data types are documented in the "Change Analysis" section of the Common Information Model Field Reference in the Data Source Integration Manual in the Splunk App for PCI Compliance documentation - http://docs.splunk.com/Documentation/PCI/DataSource/CommonInformationModelFieldReference#Change_Analysis
Note: All changes are backwards compatible with Enterprise Security 2.0.x, which does not yet conform to the updated model.
 
Use this add-on:
----------------------------------------
Configuration: Manual
Ports for automatic configuration: None
Scripted input setup: Not applicable
 
 
The Splunk Add-on for Windows supports multiple products. The methods to incorporate each log type varies. Below is a breakdown of the various log types and how to enable them.
    
    _____________________________________
    Microsoft DHCP Server:
    The Microsoft DNS server stores Microsoft DHCP server logs in a text file. These files can be imported by monitoring the file directly and manually assigning a source type of DhcpSrvLog. By default, the logs are stored in %windir%\System32\Dhcp. See "Analyze DHCP Server log files" (http://technet.microsoft.com/en-us/library/dd183591(WS.10).aspx).
    
    _____________________________________
    Windows Event Logs:
    Windows event logs can be collected with a Splunk forwarder, remotely via WMI, or by accepting them via a third party syslog daemon (such as Snare or Monitorware). If using syslog, add a data input that corresponds to the product that forwards the logs.
 
Here is an example input (in transforms.conf) that processes Windows Event Log data from Snare:
    
         [source::udp:514]
         SHOULD_LINEMERGE=false
         TRANSFORMS-force_sourcetype_for_snare_syslog = force_sourcetype_for_snare
         TRANSFORMS-force_host_for_snare_syslog = force_host_for_snare
         TRANSFORMS-force_source_for_snare_syslog = force_source_for_snare
    
    To obtain Windows event logs from deployed Splunk forwarders, see deployment-apps/README
    To obtain Windows event logs via WMI, configure WMI through the Splunk Enterprise documentation: http://docs.splunk.com/Documentation/Splunk/latest/Data/MonitorWMIdata
   
    ** To collect Windows event logs via NTSyslog, do the following:
    1.  Disable the replication blacklist for ntsyslog_mappings.csv in $SPLUNK_HOME/etc/apps/Splunk_TA_windows/local/distsearch.conf:
    [replicationBlacklist]
    nontsyslogmappings = 
    
    2.  Enable the following setting in $SPLUNK_HOME/etc/apps/Splunk-TA-windows/local/props.conf:
    [source::NTSyslog:Security]
    LOOKUP-2action_EventCode_for_ntsyslog = ntsyslog_mappings NTSyslogID OUTPUTNEW action,EventCode,EventCode as signature_id
    
    _____________________________________
    Windows Update Logs:
    The Splunk Add-on for Windows automatically discovers Windows update logs within Windows event logs. Read "Windows event logs."
   
    _____________________________________
    Microsoft Internet Authentication Service (IAS):
    The Splunk Add-on for Windows automatically discovers Microsoft Internet Authentication Service logs within Windows event logs. Read "Windows Event Logs."
    
    _____________________________________
    Windows Registry:
    See http://docs.splunk.com/Documentation/Splunk/latest/Data/MonitorWindowsregistrydata for information on how to monitor the Registry.
   

 Copyright (C) 2005-2014 Splunk Inc. All Rights Reserved.
