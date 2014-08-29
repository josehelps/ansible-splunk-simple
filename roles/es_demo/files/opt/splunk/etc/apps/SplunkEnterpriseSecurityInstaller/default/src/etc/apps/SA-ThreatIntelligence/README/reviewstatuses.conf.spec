# Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
#
# This file contains all possible options for an reviewstatuses.conf file.  Use this file to configure 
# Splunk's event generation properties.
#
# To generate events place an reviewstatuses.conf in $SPLUNK_HOME/etc/apps/SA-ThreatIntelligence/local/. 
# For examples, see reviewstatuses.conf.example. You must restart Splunk to enable configurations.
#
# To learn more about configuration files (including precedence) please see the documentation 
# located at http://www.splunk.com/base/Documentation/latest/Admin/Aboutconfigurationfiles
#
# CAUTION:  You can drastically affect your Splunk installation by changing these settings.  
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are not sure how 
# to configure this file.
#

[default]
disabled = 0
label =
description =
default = 0
selected = 0
hidden = 0
end = 0

[<status_id>]
   * <status_id> is a primary key representing the review status value of a notable event.
   * If notable events have been assigned this key (or you are unsure), do NOT modify.
   
disabled = [0|1]
    * Enable (0) or disable (1) this status.
    * Should not imply hidden.
    * Defaults to 0.

label = <string>
   * label is a string representing the review status label of a notable event (as opposed to <status_id>).
   * Defaults to None.
   
description = <string>
   * description is a string that describes the review status.
   * Defaults to None.
   
default = [1|0]
   * Set as default (1) or not (0).
   * Should not imply selected.
   * Only one default status is allowed.
   * Defaults to 0.
   
selected = [1|0]
    * Select (1) or unselect (0) this status.
    * If selected == 1, this status value will be selected when loading applicable status UI elements (Pulldowns).
    * selected == 1 can be applied to multiple <status_id> values for use with multiple selection Pulldowns.
    * If selected == 1 is enabled for multiple <status_id> values, single selection Pulldowns will select the 
      first <status> based on alphanumeric precedence.
    * Defaults to 0.
    
hidden = [1|0]
    * Hide (1) or unhide (0) this status.
    * When a status is disabled it will still be available in applicable status UI elements (Pulldowns).
    * This allows one to search on events assigned to a disabled status.
    * Defaults to 0.
    
end = [1|0]
	* Set as end status (1) or not (0).
	* Defaults to 0.