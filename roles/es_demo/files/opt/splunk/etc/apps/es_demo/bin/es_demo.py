'''
@author bluger@splunk.com
@version: 0.06.26.2014

Demo Updater

NOTE: MUST BE RUN USING SPLUNKS PYTHON: I.E. $SPLUNK_HOME$/BIN/SPLUNK CMD PYTHON
'''
import os.path
import sys
import re
from datetime import datetime
from datetime import timedelta
from optparse import OptionParser
import subprocess
import types
import string
import copy

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

class DemoUpdater(object):
    """
    Demo Updater
    """
    
    ## Saved Searches to be configured for the demo.
    ## Format: { <app_name>: {  <stanza_1>: {
    ##                              <field1>: <value1>,
    ##                              <field2>: <value2>
    ##                          }, 
    ##                          <stanza_2>: {
    ##                              <field1>: <value1>
    ##                          }
    ##            },
    ##            <app_name2>: ... etc...
    ##         }
    _savedsearches_conf = { 
            'SplunkEnterpriseSecuritySuite': {
                '[Demo - Trojan_Zbot Infections]': {
                    'action.keyindicator': '1',
                    'action.keyindicator.drilldown_uri': '''risk_analysis?form.source=Endpoint - Demo - Trojan_Zbot - Rule&form.risk_object_form=&earliest=-24h%40h&latest=now&form.risk_object_type=system''',
                    'action.keyindicator.invert': '0',
                    'action.keyindicator.subtitle': 'Number of Trojan_Zbot Infections in the environment.',
                    'action.keyindicator.threshold': '1',
                    'action.keyindicator.title': 'Demo - Trojan_Zbot Infections',
                    'action.keyindicator.value': 'current_count',
                    'action.keyindicator.delta': 'delta',
                    'alert.track': '0',
                    'search': '''| tstats allow_old_summaries=true dc(Malware_Attacks.dest) as "count" from datamodel=Malware where   nodename=Malware_Attacks Malware_Attacks.signature="Trojan.Zbot" by "Malware_Attacks.dest" | rename "Malware_Attacks.dest" as "dest" | stats count as current_count | `get_delta`''' 
                }
            },
            'DA-ESS-EndpointProtection': {
                '[Endpoint - High Number Of Infected Hosts - Rule]': {
                    'disabled': 'False',
                    'cron_schedule': '*/5 * * * *',
                },
                '[Endpoint - High Or Critical Priority Host With Malware - Rule]': {
                    'disabled': 'False',
                    'cron_schedule': '*/5 * * * *',
                    'dispatch.earliest_time': '-48h',
                    'dispatch.latest_time': '+0s',
                },
                '[Endpoint - Outbreak Observed - Rule]': {
                    'disabled': 'False',
                    'cron_schedule': '*/5 * * * *',
                    'dispatch.earliest_time': '-48h',
                    'dispatch.latest_time': '+0s',
                }
            },
            'DA-ESS-NetworkProtection': {
                '[Network - High Volume of Traffic from High or Critical Host - Rule]': {
                    'disabled': 'False',
                    'cron_schedule': '*/5 * * * *',
                    'dispatch.earliest_time': '-48h',
                    'dispatch.latest_time': '+0s',
                },
                '[Network - Unusual Volume of Network Activity - Rule]': {
                    'disabled': 'False',
                    'cron_schedule': '*/5 * * * *',
                    'dispatch.earliest_time': '-48h',
                    'dispatch.latest_time': '+0s',
                },
                '[Network - Demo Suspicious URL Request - Rule]': {
                    'action.email.sendresults': '0',
                    'action.risk': '1',
                    'action.risk._risk_object': 'src',
                    'action.risk._risk_object_type': 'system',
                    'action.risk._risk_score': '40',
                    'alert.suppress': '1',
                    'alert.suppress.fields': 'src,url,_time',
                    'alert.suppress.period': '86300',
                    'alert.track': '0',
                    'cron_schedule': '*/5 * * * *',
                    'disabled': 'False',
                    'dispatch.earliest_time': '-48h',
                    'dispatch.latest_time': '+0s',
                    'enableSched': '1',
                    'is_visible': '1',
                    'search': '''| datamodel "Web" "Web" search | rex field=Web.url "(?<=\:\/\/)(?<suspicious_ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" | where isnotnull(suspicious_ip) | stats count by Web.src, suspicious_ip, Web.url, _time | rename Web.src as src, Web.url as url'''
                }
            },
            'SA-ThreatIntelligence': {
                '[Threat - Threat List Activity - Rule]': {
                    'disabled': 'False',
                    'cron_schedule': '*/5 * * * *',
                    'dispatch.earliest_time': '-48h',
                    'dispatch.latest_time': '+0s',
                }
            },
            'SA-AccessProtection': {
                '[Access - Brute Force Access Behavior Detected - Rule]': {
                    'disabled': 'False',
                    'cron_schedule': '*/5 * * * *',
                    'dispatch.earliest_time': '-48h',
                    'dispatch.latest_time': '+0s',
                }
            },
            'SA-EndpointProtection': {
                '[Endpoint - Demo - Trojan_Zbot - Rule]': {
                    'action.email.include.results_link': '0',
                    'action.email.include.view_link': '0',
                    'action.email.reportServerEnabled': '0',
                    'action.keyindicator.invert': '0',
                    'action.risk': '1',
                    'action.risk._risk_object': 'dest',
                    'action.risk._risk_object_type': 'system',
                    'action.risk._risk_score': '80',
                    'action.summary_index': '1',
                    'action.summary_index._name': 'notable',
                    'action.summary_index.ttl': '1p',
                    'alert.suppress': '1',
                    'alert.suppress.fields': 'dest',
                    'alert.suppress.period': '86300',
                    'alert.track': '0',
                    'cron_schedule': '*/5 * * * *',
                    'disabled': 'False',
                    'dispatch.earliest_time': '-48h',
                    'dispatch.latest_time': '+0s',
                    'enableSched': '1',
                    'is_visible': '0',
                    'realtime_schedule': '0',
                    'search' : '''| tstats allow_old_summaries=true dc(Malware_Attacks.dest) as "count" from datamodel=Malware where   nodename=Malware_Attacks Malware_Attacks.signature="Trojan.Zbot" by "Malware_Attacks.dest" | rename "Malware_Attacks.dest" as "dest"'''
                }
            },
            'SA-NetworkProtection': {
                '[Network - Vulnerability Scanner Detection (by event) - Rule]': {
                    'disabled': 'False',
                    'cron_schedule': '*/5 * * * *',
                    'dispatch.earliest_time': '-48h',
                    'dispatch.latest_time': '+0s',
                },
                '[Network - Vulnerability Scanner Detection (by targets) - Rule]': {
                    'disabled': 'False',
                    'cron_schedule': '*/5 * * * *',
                    'dispatch.earliest_time': '-48h',
                    'dispatch.latest_time': '+0s',
                }
            }
    }
    
    ## Correlation Searches to be configured for the demo.
    ## Format: { <app_name>: {  <stanza_1>: {
    ##                              <field1>: <value1>,
    ##                              <field2>: <value2>
    ##                          }, 
    ##                          <stanza_2>: {
    ##                              <field1>: <value1>
    ##                          }
    ##            },
    ##            <app_name2>: ... etc...
    ##         }
    _correlationsearches_conf = {
            'DA-ESS-NetworkProtection': {
                '[Network - Demo Suspicious URL Request - Rule]': {
                    'description': 'Increases the risk score of systems that request resources from a URL using an IP instead of a Domain.',
                    'rule_name': 'Demo - Network - Suspicious URL Request',
                    
                }
            },
            'SA-ThreatIntelligence': {
                '[Threat - Threat List Activity - Rule]': {
                    'severity': 'high'
                }
            },
            'SA-EndpointProtection': {
                '[Endpoint - Demo - Trojan_Zbot - Rule]': {
                    'description': 'Detect Trojan_Zbot',
                    'drilldown_name' : 'Drill-down into Trojan_Zbot Events for $dest$',
                    'drilldown_search' : '''| datamodel "Malware" "Malware_Attacks" search | where 'Malware_Attacks.signature'="Trojan.Zbot" AND 'Malware_Attacks.dest'="$dest$"''',
                    'rule_description' : 'Trojan_Zbot was detected on $dest$!',
                    'rule_name' : 'Demo - Trojan_Zbot',
                    'rule_title' : 'Trojan_Zbot Detected on $dest$',
                    'search' : '''{"searches":[{"datamodel":"Malware","object":"Malware_Attacks","earliest":"-48h","latest":"+0s","alert.suppress.fields":["Malware_Attacks.dest"],"alert.suppress":1,"aggregates":[{"function":"dc","attribute":"Malware_Attacks.dest","alias":"count"}],"eventFilter":"Malware_Attacks.signature=\"Trojan.Zbot\"","splitby":[{"attribute":"Malware_Attacks.dest","alias":"dest"}]}],"version":"1.0"}''',
                    'security_domain' : 'endpoint',
                    'severity' : 'critical',
                    'default_owner': '',
                    'default_status': '',
                    'disabled': 'False'
                }
            }
    }
    
    ## authorize.conf configuration for the local system authorize.conf file.
    ## Format: {<stanza_1>: {<field_1>: <value_1>, <field_2>: field_3>},
    ##          <stanza_2>: {<field_1>: <value_1>, etc...
    ##         }}
    _authorize_conf = {
            '[role_user]': {
                'srchIndexesAllowed': '*;_*;es_demo',
                'srchIndexesDefault': 'es_demo;main;os'
            }
    }
    
    ## local.meta configuration for our demo app.
    ## To be merged with the ES local.meta
    _local_meta_data = {
            '[event_renderers]': {
                'export': 'none'
            },
            '[views/correlation_search_edit]': {
                'export': 'none'
            },
            '[views/notable_suppression_new]': {
                'export': 'none'
            },
            '[workflow_actions]': {
                'export': 'none'
            },
            '[]': {
                'import': 'DA-ESS-AccessProtection,DA-ESS-EndpointProtection,DA-ESS-IdentityManagement,DA-ESS-NetworkProtection,es_demo',
                'access': 'read : [ * ], write : [ admin ]',
                'export': 'system'
            },
            '[savedsearches]': {
                'owner': 'admin'
            },
            '[governance]': {
                'access': 'read : [ * ], write : [ * ]'
            },
            '[postprocess]': {
                'access': 'read : [ * ], write : [ * ]'
            },
            '[alert_actions/email]': {
                'export': 'none'
            }
    }
    
    ## Log Timestamp Regexes
    ## Note: If additional logs are added to the demo that contain timestamps 
    ##    that aren't matched by these regex definitions. Add the new 
    ##    definition here as a constant. Then add it to the _rex_dict in the 
    ##    class's constructor method along with its time formatter (use 'None'
    ##    if it's an epoch timestamp). This will ensure that the log gets 
    ##    updated.
    DNS_BRO_REX = r'^\d{10}(?=\.\d{6}\s{1})'
    ## The BLUECOAT Rex also captures the SEP Events log time. (Event,Inserted,
    ## and End Times)
    BLUECOAT_REX = r'\d{4}\-\d{2}\-\d{2}\s{1}\d{2}\:\d{2}\:\d{2}'
    ACCESS_REX = (r'(?<=\[)\d{2}\/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|' + 
                  r'Nov|Dec)\/\d{4}\:\d{2}\:\d{2}\:\d{2}(?=\s{1}\-\d{4}\])')
    IRONPORT_REX = (r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s{1}(Jan|Feb|Mar|Apr|' + 
                    r'May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s{1}\d{2}\s{1}\d{2}\:' + 
                    r'\d{2}\:\d{2}\s{1}\d{4}(?=\s{1})')
    CARBON_BLACK_REX = r'(?<=\"timestamp\"\:\s{1})\d{10}'
    EMAIL_REX = (r'(?<=\s{1})(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\,\s{1}\d{2}\s{1}' + 
                 r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s{1}' + 
                 r'\d{4}\s{1}\d{2}\:\d{2}\:\d{2}(?=\s{1}\-\d{4})')
    SEP_GENERIC_REX = (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|' + 
                         r'Dec)\s{1}\d{2}\s{1}\d{2}\:\d{2}\:\d{2}(?=\s{1})')
    WMI_REX = r'^\d{4}\d{2}\d{2}\d{2}\d{2}\d{2}(?=\.\d{6}$)'
    UNIX_REX = (r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s{1}(Jan|Feb|Mar|Apr|May|' + 
                r'Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s{3}\d{1,2}\s{1}\d{2}\:\d{2}' + 
                r'\:\d{2}\s{2}\d{4}')
    WIN_REX = r'\d{1,2}\/\d{1,2}\/\d{4}\s{1}\d{1,2}\:\d{1,2}\:\d{1,2}'
    EVENT_LOG_REX = r'\d{2}\/\d{2}\/\d{4}\s{1}\d{2}\:\d{2}\:\d{2}\s{1}(AM|PM)'
    CCNUM_REX = (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s{1}' + 
                 r'\d{2}\s{1}\d{4}\s{1}\d{2}\:\d{2}\:\d{2}')
    DHCP_REX = r'\d{2}\/\d{2}\/\d{2}\,\d{2}\:\d{2}\:\d{2}'
    FORT_FIELD_REX = (r'date\=\d{4}\-\d{2}\-\d{2}\,time\=\d{2}\:\d{2}\:\d{2}')
    WHOIS_REX = (r'((?<=\"date\"\:\s{1}\")|(?<=\"created\"\:\s{1}\")|(?<=\"' + 
                 r'updated\"\:\s{1}\"))\d{4}\-\d{2}\-\d{2}(?=\")')
    
    
    ## Regex Dictionary containing String Replacements
    _rex_dict = None
    
    ## Current time
    _current_datetime = None
    _roll_back = None
    
    ## Splunk bin path
    _splunk_bin_path = None
    
    def __init__(self):
        """
        DemoUpdater Constructor
        """
        ## Set Splunk bin path.
        self._splunk_bin_path = make_splunkhome_path(['bin']) 
        
        ## Generate current time
        self._current_datetime = datetime.now()
        
        ## Calculate log roll back time as a time delta
        self._roll_back = datetime(self._current_datetime.year,
                                   self._current_datetime.month,
                                   self._current_datetime.day)
        self._roll_back += timedelta(days=1)
        self._roll_back -= self._current_datetime
        
        ## Populate our regex dictionary
        #    The format of this dictionary is {<regex>: <time_formatter>}. The
        #    time formatter is used to output the matching regex item in that
        #    specific time format after it's been updated.
        self._rex_dict = {
            self.DNS_BRO_REX: None,
            self.BLUECOAT_REX: "%Y-%m-%d %H:%M:%S",
            self.ACCESS_REX: "%d/%b/%Y:%H:%M:%S",
            self.IRONPORT_REX: "%a %b %d %H:%M:%S %Y",
            self.CARBON_BLACK_REX: None,
            self.EMAIL_REX: "%a, %d %b %Y %H:%M:%S",
            self.SEP_GENERIC_REX: "%b %d %H:%M:%S",
            self.WMI_REX: "%Y%m%d%H%M%S",
            self.UNIX_REX: "%a %b   %d %H:%M:%S  %Y",
            self.WIN_REX: "%m/%d/%Y %H:%M:%S",
            self.CCNUM_REX: "%b %d %Y %H:%M:%S",
            self.DHCP_REX: "%m/%d/%y,%H:%M:%S",
            self.FORT_FIELD_REX: "date=%Y-%m-%d,time=%H:%M:%S",
            self.EVENT_LOG_REX: "%m/%d/%Y %H:%M:%S %p",
            self.WHOIS_REX: "%Y-%m-%d"
        }
        
    def _mergeConfDicts(self, conf_dict, conf_dict_additions):
        """
        Private Method: _mergeConfDicts
            Used to merge the contents of <tt>conf_dict_additions</tt> with the
            contents of <tt>conf_dict</tt>.
            
        @param conf_dict: Primary dictionary to which content will be added.
        @param conf_dict_additions: Secondary dictionary containing the contents
        to be added to the primary dictionary, <tt>conf_dict</tt>
        
        @return: A new dictionary containing the merged contents of both 
        dictionaries.
        
        @raise Exception: <tt>if type(conf_dict) is not types.DictType or 
        type(conf_dict_additions) is not types.DictType</tt> 
        """
        if type(conf_dict) is types.DictType and \
        type(conf_dict_additions) is types.DictType:
            copy_conf_dict = copy.deepcopy(conf_dict)
            for stanza in conf_dict_additions:
                if stanza in copy_conf_dict:
                    copy_conf_dict[stanza].update(conf_dict_additions[stanza])
                else:
                    copy_conf_dict[stanza] = conf_dict_additions[stanza]
                
            return copy_conf_dict
        else:
            raise Exception("Something other than a DictType was passed " + 
                            "in as a parameter!")
                
    
    def _confStringToDict(self, conf_string):
        """
        Private Method: _confStringToDict
            Used to convert a String representation of a Splunk .conf file to a
            Python dictionary type.
            
        @param conf_string: String representation of a Splunk .conf file.
        
        @return: A Python dictionary of type DictType representing the Splunk
        .conf file in the format: { <stanza_1>: {
                                        <field_1>: <value_1>, 
                                        <field_2>: field_3>
                                    },
                                    <stanza_2>: {
                                        <field_1>: <value_1>, 
                                        etc... 
                                    }}
                                    
        @raise Exception: <tt>if conf_string not in types.StringTypes</tt>
        """
        conf_dict = {}
        if type(conf_string) in types.StringTypes:
            conf_string = conf_string.split('\n')
            current_stanza = ''
            for line in conf_string:
                line = string.strip(line)
                if line:
                    ## Skip comment lines
                    if line[0] == "#":
                        continue
                    ## If stanza and stanza not already in conf_dict...
                    elif (line[0] == '[' and line[-1] == ']'):
                        current_stanza = line
                        if current_stanza not in conf_dict:
                            conf_dict[current_stanza] = {}
                    elif '=' in line:
                        split_index = line.find('=')
                        field = string.strip(line[:split_index])
                        value = string.strip(line[split_index + 1:])
                        conf_dict[current_stanza][field] = value
        else:
            raise Exception("Something other than a String was passed in " + 
                            "as an parameter!")
                    
        return conf_dict
        
    def _confDictToString(self, conf_dict):
        """
        Private Method: _confDictToString
            Used to convert a Python dictionary representation of a Splunk .conf
            file of type DictType to a String representation of a Splunk .conf
            file of type StringTypes.
            
        @param conf_dict: A Python dictionary representation of a Splunk .conf 
        file of type DictType
        
        @return: A String representation of the Splunk .conf file.
        
        @raise Exception: <tt>if conf_dict is not types.DictType</tt>
        """
        conf_string = ''
        if type(conf_dict) is types.DictType:
            for stanza in conf_dict:
                conf_string += stanza + '\n'
                for statement in sorted(conf_dict[stanza]):
                    conf_string += (statement + ' = ' + 
                                    conf_dict[stanza][statement] + '\n')
                conf_string += '\n'
        else:
            raise Exception("Illegal field type was passed to this function! " + 
                            "Field must be a DictType!")
            
        return conf_string
        
    def _appendToConf(self, conf_path, content, overwrite=False):
        """
        Private Method: _appendToConf
            Used to append the content defined in <tt>content</tt> to the .conf
            file found at <tt>conf_path</tt>.
        @param conf_path: Path to the conf file that will be appended.
        @param content: A Dictionary containing the entries that need to be 
            added to the conf file in the following format:
            {<stanza>: {<field1>: <value1>, <field2>: <value2>, etc...}}
        @param overwrite: <tt>true</tt> to overwrite the existing conf file,
            <tt>false</tt> to merge with it.
            
        @return: <tt>True</tt> if content was successfully appended, 
        <tt>False</tt> otherwise.
        
        @raise Exception: <tt>if type(conf_path) not in types.StringTypes or 
        type(content) is not types.DictType</tt> 
        """
        success = False
        full_conf_path = None
        
        if type(conf_path) in types.StringTypes:
            ## Seperate file from file path.
            file_sep = len(conf_path) - conf_path[::-1].find('/')
            conf_file = conf_path[file_sep:]
            conf_path = os.path.normpath(conf_path[:file_sep])
            
            ## Create directory structure if it doesn't exist.
            if not os.path.exists(conf_path):
                os.makedirs(conf_path)
                
            full_conf_path = os.path.join(conf_path, conf_file)
        else:
            raise Exception("Something other than StringTypes was passed in " + 
                            "for the conf_path parameter!")
        
        if type(content) is types.DictType:
            if os.path.exists(full_conf_path):
                conf_string = ''
                with open(full_conf_path, 'rb') as conf_handle:
                    conf_string = conf_handle.read()
                    
                conf_dict = self._confStringToDict(conf_string)
                
                if not overwrite:
                    content = self._mergeConfDicts(conf_dict, content)
      
            with open(full_conf_path, 'wb') as conf_handle:
                conf_handle.write(self._confDictToString(content))
                
            success = True
        else:
            raise Exception("Something other than a dictionary was passed " + 
                            "in for the content parameter!")
            
        return success
                
        
    def _updateLog(self, log_content, delimiter):
        """
        Private Method: _updateLog
            Used to update the content of the log so that all timestamps within
            the log that match our regex definitions will appear to have
            occurred within the past 24 hours.
            
        @param log_content: The String content of the log file.
        @param delimiter: The delimiter used in the log content to separate  
            lines.
            
        @return: The log content with updated timestamps.
        """
        updated_log = ""
        for line in log_content.split(delimiter):
            if line:
                updated_line = line
                for rex in self._rex_dict:
                    match = re.search(rex, updated_line)
                    if match:
                        updated_log_time = ""
                        match = match.group(0)
                        if self._rex_dict[rex]:
                            ## parse using datetime formatter
                            log_time = datetime.strptime(match, 
                                                         self._rex_dict[rex])
                            updated_log_time = self._updateTime(log_time, 
                                                           self._rex_dict[rex])
                        else:
                            ## It's an epoch time and can't be parsed using 
                            ## a datetime formatter
                            match = int(match)
                            log_time = datetime.fromtimestamp(match)
                            updated_log_time = self._updateTime(log_time, "%s")
                        
                        ## Update line entry with new timestamp
                        updated_line = re.sub(rex, updated_log_time, 
                                              updated_line)
                        
                ## Add updated line entry to our updated log.
                updated_log += updated_line + delimiter
        
        return updated_log
        
    def _updateTime(self, log_time, time_formatter):
        """
        Private Method: _updateTime
            Used to update the event time of the log entry so that it appears
                to have occured within the past 24 hours.
            
        @param log_time: A datetime object representing a timestamp from a log.
        @param time_formatter: The time formatter for the updated log entry.
            Note: This is the format for the updated time that will replace the
            actual time of the log.
            
        @raise Exception: <tt>if not (last_24 <= updated_time 
            <= self._current_datetime)</tt>
            
        @return A string representation, specified by <tt>time_formatter</tt>,
            of the updated log timestamp.
        """
        ## Update Log time to the current day.
        updated_time = datetime(self._current_datetime.year,
                                self._current_datetime.month,
                                self._current_datetime.day,
                                log_time.hour,
                                log_time.minute,
                                log_time.second)
        
        ## Roll back the updated log time so that it fits within a period of
        ##   the last 24 hours.
        updated_time -= self._roll_back
        
        ## Last 24 hours with a grace period of 5 minutes.
        last_24_hours = self._current_datetime - timedelta(days=1, seconds=300)
        
        ## If our new log time doesn't fall within this time frame, raise an
        ## exception so that the problem can be handled.
        if not (last_24_hours <= updated_time <= self._current_datetime):
            raise Exception("ERROR: Updated time falls outside of the last " + 
                            "25 hours!")
        
        return datetime.strftime(updated_time, time_formatter)
        
    def updateLogFiles(self, log_dir):
        """
        Public Method: updateLogFiles
            Updates all timestamps that match the regex patterns in 
            <tt>self._rex_dict</tt> for all public files within the given 
            directory.
            
        @param log_dir: The directory the log files are contained in.
        """
        print str(datetime.utcnow()) + ": Updating Log Files..."
        ## Get Log Content
        log_dir = os.path.normpath(log_dir)
        log_files = os.walk(log_dir).next()[2]
        log_content = {}
        for log_file in log_files:
            if log_file[0] != '.':
                file_path = log_dir + os.path.sep + log_file
                with open(file_path, 'rb') as file_handle:
                    log_content[file_path] = file_handle.read()
        
        ## Update Log Content and write to disk
        for log in log_content:
            try:
                log_content[log] = self._updateLog(log_content[log], '\n')
                with open(log, 'wb') as file_handle:
                    file_handle.write(log_content[log])
                print str(datetime.utcnow()) + ': SUCCESS: ' + log + ' updated!'
            except Exception as e:
                print (str(datetime.utcnow()) + ": ERROR: Unable to update: " + 
                       str(log))
                print str(datetime.utcnow()) + ": " + str(e)
                continue
        
        print '\n',
        
    def cleanSplunkIndexes(self):
        """
        Public Method: cleanSplunkIndexes
            Used to issue '$SPLUNK_HOME/bin/splunk clean all -f' to Splunk in 
            order to clean all splunk indexes.
        """
        print str(datetime.utcnow()) + ': Cleaning Splunk Indexes...'
        try:
            p = subprocess.Popen([os.path.join(self._splunk_bin_path, 'splunk'), 
                                 'clean', 'all', '-f'], 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            out, err = p.communicate()
            
            if err:
                raise Exception(err)
            
            print out
            
        except Exception as e:
            print (str(datetime.utcnow()) + ': There was an error attempting to ' + 
                   'clean the Splunk Indexes:')
            print str(datetime.utcnow()) + ": " + str(e)
    
    def issueSplunkCommand(self, command):
        """
        Public Method: issueSplunkCommand
            Used to issue one of 'stop, start' commands to splunk via its CLI.
        
        @param command: The command to be issued to splunk via its CLI. Must 
        be one of ['stop', 'start'].
        
        @raise Exception: <tt>if command is not in ['start', 'stop']</tt>
        """
        if command in ['stop', 'start']:
            if command is 'start':
                print str(datetime.utcnow()) + ': Starting Splunk...'
            else:
                print str(datetime.utcnow()) + ': Stopping Splunk...'
            try:
                p = subprocess.Popen([os.path.join(self._splunk_bin_path, 
                                                  'splunk'), 
                                     command, '-f'], stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
                
                out, err = p.communicate()
                
                if err:
                    raise Exception(err)
                
                print out
            except Exception as e:
                print (str(datetime.utcnow()) + ': There was an issue trying to ' + 
                command + ' splunk.')
                print str(datetime.utcnow()) + ": " + str(e)
        else:
            raise Exception("Command must be one of: [start, stop]!")
    
    def configureSavedSearches(self):
        """
        Public Method: configureSavedSearches
            Used to configure all saved searches found within 
                <tt>_savedsearches_conf</tt>.
        """
        print str(datetime.utcnow()) + ": Configuring Required Saved Searches..."
        for app in self._savedsearches_conf:
            local_conf_path = make_splunkhome_path(['etc', 'apps', app, 'local', 
                                                    'savedsearches.conf'])
            success = self._appendToConf(local_conf_path, 
                                         self._savedsearches_conf[app],
                                         overwrite=True)
            
            if success:
                print (str(datetime.utcnow()) + ": SUCCESS: " + app + 
                       ": savedsearches.conf " + "successfully configured!")
            else:
                print (str(datetime.utcnow()) + ": " + app + 
                       ": ERROR: Unable to configure savedsearches.conf!")
                
        print '\n',
        
    def configureCorrelationSearches(self):
        """
        Public Method: configureCorrelationSearches
            Used to configure all correlation searches found within 
                <tt>_correlationsearches_conf</tt>.
        """
        print (str(datetime.utcnow()) + ": Configuring Required Correlation " + 
               "Searches...")
        for app in self._correlationsearches_conf:
            local_conf_path = make_splunkhome_path(['etc', 'apps', app, 'local', 
                                                    'correlationsearches.conf'])
            success = self._appendToConf(local_conf_path, 
                                         self._correlationsearches_conf[app],
                                         overwrite=True)
            
            if success:
                print (str(datetime.utcnow()) + ": SUCCESS: " + app + 
                       ": correlationsearches.conf successfully configured!")
            else:
                print (str(datetime.utcnow()) + ": " + app + 
                       ": ERROR: Unable to configure correlationsearches.conf!")
                
        print '\n',
        
    def configureAuthorizeConf(self):
        """
        Public Method: 
            Used to configure the local system authorize.conf.
        """
        print (str(datetime.utcnow()) + ": Configuring System Local " + 
               "authorize.conf...")
        local_system_path = make_splunkhome_path(['etc', 'system', 'local', 
                                                  'authorize.conf'])
        
        success = self._appendToConf(local_system_path, self._authorize_conf)
        
        if success:
            print (str(datetime.utcnow()) + ": SUCCESS: System Local " + 
                   "authorize.conf successfully configured!")
        else: 
            print (str(datetime.utcnow()) + ": ERROR: Unable to configure local " + 
                   "system authorize.conf!")
            
        print '\n',
        
    def configureLocalMetaData(self):
        """
        Public Method:
            Used to configure the .../metadata/local.meta of the 
            SplunkEnterpriseSecuritySuite app so as to make it compatible with
            our demo application. It does this by merging 
            <tt>self._local_meta_data</tt> with 
            .../SplunkEnterpriseSecuritySuite/metadata/local.meta 
        """
        print (str(datetime.utcnow()) + ": Configuring SplunkEnterprise" + 
               "SecuritySuite Local Meta Data...")
        local_meta_path = make_splunkhome_path(['etc', 'apps', 
                                                'SplunkEnterpriseSecuritySuite', 
                                                'metadata', 'local.meta'])
        
        success = self._appendToConf(local_meta_path, self._local_meta_data)
        
        if success:
            print (str(datetime.utcnow()) + ": SUCCESS: SplunkEnterpriseSecurity" + 
                   "Suite Local Meta Data successfully configured!")
        else:
            print (str(datetime.utcnow()) + ": ERROR: Unable to configure Splunk" + 
                   "EnterpriseSecuritySuite Local Meta Data!")
            
        print '\n',
        
    def replaceLookupTable(self, path_of_replacee, path_of_replacement):
        """
        Public Method:
            Used to replace one lookup file with another.
        
        @param path_of_replacee: The path of the lookup file to be replaced.
        @param path_of_replacement: The path of the replacement lookup file.
        
        @raise Exception: If the column headers between the too csv files are
        inconsistent with one another.
        """
        
        print (str(datetime.utcnow()) + ': Attempting to replace ' + 
               path_of_replacee + ' with ' + path_of_replacement + '...')
        
        with open(path_of_replacee, 'rb') as replacee:
            with open(path_of_replacement, 'rb') as replacement:
                if replacee.readline().split(',') != \
                replacement.readline().split(','):
                    raise Exception("Inconsistent Column Headers!")
        
        with open(path_of_replacement, 'rb') as replacement_handle:
            with open(path_of_replacee, 'wb') as replacee_handle:
                replacee_handle.write(replacement_handle.read())
                
        print (str(datetime.utcnow()) + ': SUCCESS: Replaced ' + path_of_replacee + 
               ' with ' + path_of_replacement)

        print '\n',
                
if __name__ == '__main__':
    """
    Main Function for using our LogUpdater Python Script.
    """
    parser = OptionParser()
    parser.add_option("-r", "--reset-demo", action="store_true", 
                      help=("Cleans all Splunk Indexes and Updates all Log " + 
                            "Files associated with the Demo."))
    parser.add_option("-s", "--start", action="store_true", 
                      help=("Starts Splunk. (Doesn't perform any update " + 
                            "procedures)"))
    parser.add_option("-c", "--stop", action="store_true", 
                      help=("Stops Splunk. (Doesn't perform any update " + 
                            "procedures)"))
    
    (options, args) = parser.parse_args()
    
    ## If there's an incorrect number of arguments, shit bricks...
    if not (options.reset_demo or options.start or options.stop):
        print '\n'
        print (str(__name__) + ": ERROR: You must specify an action for " + 
               "the script!\n")
        parser.print_help()
        print '\n'
        sys.exit()
        
                            ##  Option Parser ##
#------------------------------------------------------------------------------#
                            ##  Updater Code  ##
    updater = DemoUpdater()
    
    if options.reset_demo:
        updater.issueSplunkCommand('stop')
        updater.cleanSplunkIndexes()
        updater.updateLogFiles(make_splunkhome_path(['etc', 
                                            'apps', 'es_demo', 'log']))
        updater.updateLogFiles(make_splunkhome_path(['etc', 'apps', 
                                    'es_demo', 'log', 'sample_noise']))
        updater.configureSavedSearches()
        updater.configureCorrelationSearches()
        updater.configureAuthorizeConf()
        updater.configureLocalMetaData()
        updater.replaceLookupTable(make_splunkhome_path(['etc', 'apps', 
            'SA-IdentityManagement', 'lookups', 'demo_assets.csv']), 
                                   make_splunkhome_path(['etc', 'apps', 
            'es_demo', 'lookups', 'demo_assets.csv']))
        updater.replaceLookupTable(make_splunkhome_path(['etc', 'apps', 
            'SA-IdentityManagement', 'lookups', 'demo_identities.csv']), 
                                   make_splunkhome_path(['etc', 'apps', 
            'es_demo', 'lookups', 'demo_identities.csv']))
        updater.issueSplunkCommand('start')
    elif options.start:
        updater.issueSplunkCommand('start')
    elif options.stop:
        updater.issueSplunkCommand('stop')