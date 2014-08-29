# McAfee EPO Technology Add-on #

## About ##
```
Author=Splunk
Version=2.0.0
Date=2014-07-01
```

### Supported product(s) ###
  * McAfee EPO (ePolicy Orchestrator) version 4.x & 5.x

### Source type(s) ###
  * mcafee:epo
  * mcafee:ids

### Input requirements ###
  * Data must be imported using a direct database extraction. 
  * DB Connect Version 1.1.4 or later
  * This TA should be placed on DB Connect instance (with appropriate inputs enabled)
	
### Parsing and/or Indexing requirements ###
  * Has parsing props
  * This TA should be placed on heavy forwarders and indexers (with inputs disabled)
  
### Searching requirements ###
  * Contains search time field extractions, aliasing, & lookups
  * This TA should be placed on search heads (with inputs disabled)
   
## Using this Technology Add-on ##

### McAfee ePo via DB Connect ###
```
Configuration: Manual
Ports for automatic configuration: None
App Pre-requisite: DB Connect version 1.1.4 or later
```

This Technology Add-on has generic parameters used by DB Connect to connect to MSSQL Database for McAfee EPO. These settings should be updated database.conf & inputs.conf file. This Technology Add-on has specific queries that poll those databases and they may be edited via the inputs.conf file. 

#### To use  ####
  * Update these configuration items in the database configuration for the version of McAfee EPO you have. **NB** It is important to update the following parameters either as a copy in this TA's local directory (database.conf) 
```
host = [host of EPO SQL Server] <-- This will be used by Splunk to locate the database
username = [domain\user_id of EPO database user]
password = [password of EPO database user]
port =[<port of EPO SQL Server instance, generally 1433]
```
  *  Enable the database for the version of McAfee EPO you have. **NB** It is important to update the following parameters either as a copy in this TA's local directory (database.conf) 
```
disabled=1
```
  * Once you've updated the configuration of and enabled the connection to the database, configure the input via this TA's local/inputs.conf 
  * __NB__ If you do not want to acquire ALL the data, adjust the "0" near the end of the SQL statement `WHERE [EPOEvents].[AutoID] > 0` (i.e. change the 0 to 20000 if you want to start reading record 20,001 and beyond)
  * __NB__ Update the host value as well. The host in inputs is for the host of the events whereas the host in database is to instruct Splunk of the server to query
  * Similar to configuring the database connection, there is a disabled version of what you need, simply enable it via conf file 
```
host = [host of EPO SQL Server] <-- This will be used by Splunk for the host of the event
disabled=1
```

### McAfee IDS via Syslog ###
```
Configruation: Manual
Ports for automatic configuration: None
App Pre-requisite: This app expects McAfee IDS data to have a sourcetype of `mcafee:ids`
```
	
## Troubleshooting ##
This section intentionally left blank. It may be updated in future versions

Copyright (C) 2009-2014 Splunk Inc. All Rights Reserved.
