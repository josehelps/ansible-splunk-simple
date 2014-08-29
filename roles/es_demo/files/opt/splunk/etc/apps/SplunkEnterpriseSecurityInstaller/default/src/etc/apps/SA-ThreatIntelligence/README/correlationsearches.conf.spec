# Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
#
# This file contains all possible options for an correlationsearches.conf file.  Use this file to configure 
# Splunk's event generation properties.
#
# To detail a correlation search place a correlationsearches.conf in $SPLUNK_HOME/etc/apps/<app>/local/. 
# For examples, see correlationsearches.conf.example.
#
# To learn more about configuration files (including precedence) please see the documentation 
# located at http://www.splunk.com/base/Documentation/latest/Admin/Aboutconfigurationfiles
#
# CAUTION:  You can drastically affect your Splunk installation by changing these settings.  
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are not sure how 
# to configure this file.
#

[default]
security_domain =
severity =
rule_name =
description =
rule_title =
rule_description =
drilldown_name =
drilldown_search =
default_status =
default_owner =
search =


[<stanza name>]
   * Create a stanza name for each correlation search.
   * Stanza name must match stanza in savedsearches.conf
   * Follow the stanza name with any number of the following attribute/value pairs.
   * If you do not specify an attribute, Splunk uses the default.

###### The following settings apply to all correlation searches ######
   
rule_name = <string>
   * Specifies the friendly name of the correlation search as an object.
   * Used to generate statistics per correlation search.
   * Does not support token replacement.
   * Required.
   * Defaults to None.

description = <string>
   * Human readable description of the correlation search as an object.
   * Does not support token replacement.
   * Optional.
   * Defaults to None.
 
search = <json>
   * Advanced search JSON specification (Appendix A).
   * Optional.
   * Defaults to None.

###### The following settings apply to correlation searches that generate notable events ######

security_domain = <access|endpoint|network|threat|identity|audit>
   * Specifies the security domain which this correlation search applies to.
   * Defaults to None.
   
severity = <informational|low|medium|high|critical>
   * Specifies the severity of the correlation search.
   * Defaults to None.

rule_title = <string>
   * Specifies the title for an instance of the correlation search.
   * Used to provide a title for an instance of the correlation search when 
     viewed within the Incident Review dashboard.
   * Supports token ($token$) replacement.
   * Defaults to None.
   
rule_description = <string>
   * A string which describes an instance of the correlation search.
   * Used to provide a description for an instance of the correlation search when 
   viewed within the Incident Review dashboard.
   * Supports token ($token$) replacement.
   * Defaults to None.
   
drilldown_name = <string>
   * A string which providing text for the drilldown hyperlink within the Incident
     Review dashboard.
   * Supports token ($token$) replacement.
   * Defaults to None.

drilldown_search = <string>
   * Actual search terms of the drilldown search.
   * Your search can include macro searches for substitution.
   * Supports token ($token$) replacement.
   * Defaults to None.

default_status = <status_id>
   * Status this correlation search should default to when triggered.
   * Defaults to None.

default_owner = <Splunk user>
   * Splunk user this correlation search should default to when triggered.
   * Defaults to None.
   
###### Appendix A: Advanced Search Specification #######
#{
#   "version":                 "<version number>",
#	"searches":              [
#		{
#			"key":          "<Field to use to link searches together>",
#
#			"datamodel":    "<Data Model Name>",
#			"object":       "<Data Model Object Name">,
#			
#			"inputlookup":  {
#				"lookupName": "<Lookup Table Name>",
#				"timeField":  "<Field to use for time based lookups>"
#			},
#
#			"earliest":     "<Earliest Time Specifier>",
#			"latest":       "<Latest Time Specifier>",
#
#			"eventFilter":  "<where clause>",
#
#			"aggregates":   [
#				{
#					"function":  "<sum|dc|etc>",
#					"attribute": "<field input name>",
#					"alias":     "<field output name>"
#				}
#			],
#
#			"splitby":      [
#				{
#					"attribute": "<field input name>",
#					"alias":     "<field output name>"
#				}
#			],
#
#			"resultFilter": {
#				"comparator": "<=|!=|>|<|etc",
#				"value":      "<value>"
#			}
#		}
#	],
#
#	"alert.suppress":        "[1|0]",
#	"alert.suppress.fields": ["<field1>","<field2>",...,"<fieldn>"]
#}
