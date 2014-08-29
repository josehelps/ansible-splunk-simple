# Copyright (C) 2005-2012 Splunk Inc. All Rights Reserved.
#
# This file contains all possible options for an tsidx_retention.conf file.  Use this file to configure 
# how Splunk's TSIDX namespaces are retained.
#
#
# To learn more about configuration files (including precedence) please see the documentation 
# located at http://docs.splunk.com/Documentation/Splunk/latest/Admin/Aboutconfigurationfiles
#
# CAUTION:  You can drastically affect your Splunk installation by changing these settings.  
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are not sure how 
# to configure this file.

# GLOBAL SETTINGS
# Use the [default] stanza to define any global settings.
#     * You can also define global settings outside of any stanza, at the top of the file.
#     * Each conf file should have at most one default stanza. If there are multiple default
#       stanzas, attributes are combined. In the case of multiple definitions of the same
#       attribute, the last definition in the file wins.
#     * If an attribute is defined at both the global level and in a specific stanza, the
#       value in the specific stanza takes precedence

[<stanza name>]
   * Create a unique stanza name for each TSIDX namespace
   * Follow the stanza name with any number of the following attribute/value pairs.
   * If you do not specify an attribute, Splunk uses the default.

maxTotalDataSizeMB = <integer>
	* The maximum size of an namespace (in MB). 
	* If an index grows larger than the maximum size, the oldest data is frozen.
	* This parameter will only have an effect if the size limit has been reached and if there exists files
      that can be deleted that does not cause the size to dip below the the limit.
	* Defaults to 500000.
	* Highest legal value is 4294967295
	* Lowest legal value is 50

retentionTimePeriodInSecs = <integer>
	* Number of seconds after which a namespace file is deleted (based on the date of the latest event).
	* IMPORTANT: Every event in the DB must be older than frozenTimePeriodInSecs before it will be deleted.
	* Defaults to 188697600 (6 years).
	* Highest legal value is 2147483647
	* Lowest legal value is 86400 (one day)