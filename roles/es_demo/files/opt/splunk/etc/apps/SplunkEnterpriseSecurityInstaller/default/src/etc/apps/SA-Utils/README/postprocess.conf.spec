# Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
#
# This file contains all possible options for an postprocess.conf file.  Use this file to configure 
# Splunk's search post process properties.
#
# To generate events place an postprocess.conf in $SPLUNK_HOME/etc/apps/SA-PostProcess/local/. 
# For examples, see postprocess.conf.example. You must restart Splunk to enable configurations.
#
# To learn more about configuration files (including precedence) please see the documentation 
# located at http://www.splunk.com/base/Documentation/latest/Admin/Aboutconfigurationfiles
#
# CAUTION:  You can drastically affect your Splunk installation by changing these settings.  
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are not sure how 
# to configure this file.
#


[<stanza name>]
   * Create a unique stanza name for each post process search.
   * Follow the stanza name with any number of the following attribute/value pairs.
   * If you do not specify an attribute, Splunk uses the default.

disabled = [0|1]
   * Disable your search by setting to 1.
   * If set to 1, this saved search is not visible in Splunk Web.
   * Defaults to 0.

savedsearch = <string>
    * Name of saved search to post process.
    * Must match stanza in savedsearches.conf.
    * savedSearch must be scheduled.
    * savedSearch must specify action.postprocess = 1.

postprocess = <string>
    * Actual search terms of the saved search.
    * For example, postProcess = stats count by host.
    * Your search can include macro searches for substitution.
    * To learn more about creating a macro search, search the documentation for "macro search."