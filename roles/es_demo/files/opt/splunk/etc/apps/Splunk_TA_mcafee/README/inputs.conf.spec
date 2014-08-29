# Copyright (C) 2005-2014 Splunk Inc. All Rights Reserved.
# This file contains the database monitor definitions

# NB: This spec file was curated from the spec file in dbx version 1.1.4, build 207870 
#     for the prupose of preventing "Possible typo in stanza" warnings during the startup
#     check of conf files for typos 

[dbmon-<type>://<database>/<unique_name>]
output.format = [kv|mkv|csv|template]
output.timestamp = [true|false]
output.timestamp.column = <string>
output.timestamp.format = <string>
output.timestamp.parse.format = <string>
query = <string>
tail.rising.column = <string>
