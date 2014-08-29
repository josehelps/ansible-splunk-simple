'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''

import xml.sax.handler
import re
import ipmath

# xml handler for targets
class NessusTargetsHandler(xml.sax.handler.ContentHandler):
    
    def __init__(self):
        
        # Targets Variables        
        self.targets = []
        self.target = { }
        self.targetCount = 0
        self.isTargetsElement = 0
        self.isTargetElement = 0
        self.isSelectedElement = 0
        self.isTypeElement = 0
        self.isValueElement = 0
        self.isStartElement = 0
        self.isEndElement = 0
        self.isNetworkElement = 0
        self.isNetmaskElement = 0
        
    def startElement(self, name, attributes):
        
        # Check for "Targets" start element
        if name == "Targets":
            self.isTargetsElement = 1
    
        # For each "Targets" start elements below, set element variable to 1 and initialize content string 
        if self.isTargetsElement == 1 and name != "Targets":    
            
            if name == "Target":
                self.isTargetElement = 1    
                
            elif name == "selected":
                self.isSelectedElement = 1
                self.targetSelected = ""    
            
            elif name == "type":
                self.isTypeElement = 1
                self.targetType = ""
            
            elif name == "value":
                self.isValueElement = 1
                self.hostnameValue = ""
            
            elif name == "start":
                self.isStartElement = 1
                self.rangeStart = ""
            
            elif name == "end":
                self.isEndElement = 1
                self.rangeEnd = ""
            
            elif name == "network":
                self.isNetworkElement = 1
                self.networkNetwork = ""
            
            elif name == "netmask":
                self.isNetmaskElement = 1
                self.networkNetmask = ""
                
    def characters (self, ch):
    
        # "Targets" "Target" specific data grabbers
        
        if self.isSelectedElement:
            self.targetSelected += ch
        
        if self.isTypeElement:
            self.targetType += ch
        
        if self.isValueElement:
            self.hostnameValue += ch
        
        if self.isStartElement:
            self.rangeStart += ch
        
        if self.isEndElement:
            self.rangeEnd += ch
        
        if self.isNetworkElement:
            self.networkNetwork += ch
        
        if self.isNetmaskElement:
            self.networkNetmask += ch
    
    def endElement(self, name):
        
        # Check for "Targets" end element
        if name == "Targets":
            self.isTargetsElement = 0
            
        # If "Targets" is set look for end elements specifically in the "Targets" tree
        if self.isTargetsElement == 1 and name != "Targets":
                
            # At "Target" end element add said element to "Targets" dictionary
            if name == "Target":
                self.isTargetElement = 0
                self.targets.append( self.target )
                self.target = { }
                self.targetCount += 1
            
            # At "Selected" set boolean mapped content to "Target" array
            elif name == "selected":
                
                if self.targetSelected == "yes":
                    self.target['Selected'] = 1
                
                elif self.targetSelected == "no":
                    self.target['Selected'] = 0
                
                else:
                    self.target['Selected'] = ""
                
                self.isSelectedElement = 0
                self.targetSelected = ""
            
            # At "type" end element set content to "Target" array
            elif name == "type":
                self.target['Type'] = str(self.targetType)
                self.isTargetElement = 0
                self.targetType = ""
            
            # At "value" end element set content (IP vs. hostname) to "Target" array
            elif name == "value":
                ipRegex = re.compile('\d+.\d+.\d+.\d+')
                ipMatch = ipRegex.match(self.hostnameValue)
                
                if ipMatch:
                    self.target['StartAddress'] = ipmath.IPToLong(ipMatch.group())
                    self.target['EndAddress'] = ipmath.IPToLong(ipMatch.group())
                    self.target['Type'] = "ip"
                else:
                    self.target['Hostname'] = self.hostnameValue
                    self.target['StartAddress'] = ""
                    self.target['EndAddress'] = ""
                
                self.isValueElement = 0
                self.hostnameValue = ""
            
            # At "start" end element set content to "Target" array
            elif name == "start":            
                self.target['StartAddress'] = ipmath.IPToLong(self.rangeStart)
                self.target['Hostname'] = ""
                self.isStartElement = 0
                self.rangeStart = ""
            
            # At "end" end element set content to "Target" array
            elif name == "end":
                self.target['EndAddress'] = ipmath.IPToLong(self.rangeEnd)
                self.isEndElement = 0
                self.rangeEnd = ""
            
            # At "network" end element set content to "Target" array
            elif name == "network":
                self.target['StartAddress'] = self.networkNetwork
                self.target['Hostname'] = ""
                self.isNetworkElement = 0
                self.networkNetwork = ""
            
            # At "netmask" end element set netmask to address range normalized content to "Target" array
            elif name == "netmask":            
                self.tempRange = ipmath.NetmaskToRange(str(self.target['StartAddress']), str(self.networkNetmask))
                self.target['StartAddress'] = ipmath.IPToLong(self.tempRange['StartAddress'])
                self.target['EndAddress'] = ipmath.IPToLong(self.tempRange['EndAddress'])
                self.isNetmaskElement = 0
                self.networkNetmask = ""
    

#
# xml handler for policies
class NessusPoliciesHandler(xml.sax.handler.ContentHandler):

    def __init__(self):
    
        # Policies Variables
        self.policies = []
        self.policy = { }
        
        self.passwordsType = ""
        
        self.policyCount = 0
        
        self.isPoliciesElement = 0
        self.isPolicyElement = 0
        self.isPolicyNameElement = 0
        self.isPolicyCommentElement = 0
        self.isPolicyUUIDElement = 0
        
        # Policies Preferences Variables
        self.serverPreferences = { }
        self.serverPreference = { }
        self.pluginsPreferences = { }
        self.item = { }
        
        self.serverPreferenceCount = 0
        self.itemCount = 0
        
        self.isPolicyPreferencesElement = 0
        self.isServerPreferencesElement = 0
        self.isServerPreferenceElement = 0
        self.isServerPreferenceNameElement = 0
        self.isServerPreferenceValueElement = 0
        self.isPluginsPreferencesElement = 0
        self.isItemElement = 0
        self.isItemFullNameElement = 0
        self.isItemPreferenceNameElement = 0
        self.isItemPreferenceTypeElement = 0
        self.isItemPluginNameElement = 0
        self.isItemPreferenceValuesElement = 0
        self.isItemSelectedValueElement = 0
        
        # Policies Plugins Variables
        self.familySelection = { }
        self.familyItem = { }
        self.individualPluginSelection = { }
        self.pluginItem = { }
        
        self.familySelectionCount = 0
        self.individualPluginSelectionCount = 0
        
        self.isPluginSelectionElement = 0
        self.isFamilySelectionElement = 0
        self.isFamilyItemElement = 0
        self.isFamilyNameElement = 0
        self.isFamilyStatusElement = 0
        self.isIndividualPluginSelectionElement = 0
        self.isPluginItemElement = 0
        self.isPluginItemIdElement = 0
        self.isPluginItemNameElement = 0
        self.isPluginItemFamilyElement = 0
        self.isPluginItemStatusElement = 0
    
    def startElement(self, name, attributes):    
        
        # Check for "Policies" start element
        #if name == "Policies": #Not used in Version 2
            #self.isPoliciesElement = 1
            
        # Check for "Policy" start element
        if name == "Policy":
            self.isPolicyElement = 1
            #self.passwordsType = attributes.get('passwordsType', None) #Not used in Version 2

        # For each "Policies" start elements below, set element variable to 1 and initialize content string
        if self.isPolicyElement == 1 and name != "Policy":
            
            if name == "policyName":
                self.isPolicyNameElement = 1
                self.policyName = ""
                
            elif name == "policyComment":
                self.isPolicyCommentElement = 1
                self.policyComment = ""
            
            #elif name == "uuid": #Not used in Version 2
                #self.isPolicyUUIDElement = 1
                #self.policyUUID = ""
            
            elif name == "Preferences":
                self.isPolicyPreferencesElement = 1
            
            # For each "Policy" "Preferences" start elements below, set element variable to 1 and initialize content string
            if self.isPolicyPreferencesElement == 1 and name != "Preferences":
                
                if name == "ServerPreferences":
                    self.isServerPreferencesElement = 1
                    
                elif name == "preference":
                    self.isServerPreferenceElement = 1
                
                elif name == "name":
                    self.isServerPreferenceNameElement = 1
                    self.serverPreferenceName = ""
                    
                elif name == "value":
                    self.isServerPreferenceValueElement = 1
                    self.serverPreferenceValue = ""
                    
                elif name == "PluginsPreferences":
                    self.isPluginsPreferencesElement = 1
                
                elif name == "item":
                    self.isItemElement = 1
                    
                # For each "Policy" "Preferences" "PluginsPreferences" "Item" start elements......
                if self.isItemElement == 1 and name != "item":
                    
                    if name == "fullName":
                        self.isItemFullNameElement = 1
                        self.itemFullName = ""
                        
                    elif name == "preferenceName":
                        self.isItemPreferenceNameElement = 1
                        self.itemPreferenceName = ""
                        
                    elif name == "pluginName":
                        self.isItemPluginNameElement = 1
                        self.itemPluginName = ""
                        
                    elif name == "preferenceType":
                        self.isItemPreferenceTypeElement = 1
                        self.itemPreferenceType = ""
                        
                    elif name == "preferenceValues":
                        self.isItemPreferenceValuesElement = 1
                        self.itemPreferenceValues = ""
                    
                    elif name == "selectedValue":
                        self.isItemSelectedValueElement = 1
                        self.itemSelectedValue = ""
            
            if name == "FamilySelection":
                self.isFamilySelectionElement = 1
                        
            if self.isFamilySelectionElement == 1 and name != "FamilySelection":
            
                if name == "FamilyItem":
                    self.isFamilyItemElement = 1
                
                elif name == "FamilyName":
                    self.isFamilyNameElement = 1
                    self.familyName = ""
                
                elif name == "Status":
                    self.isFamilyStatusElement = 1
                    self.familyStatus = ""
                
            if name == "IndividualPluginSelection":
                self.isIndividualPluginSelectionElement = 1
            
            # For each "Policy" "PluginSelection" "IndividualPluginSelection" start elements below, ...
            if self.isIndividualPluginSelectionElement == 1 and name != "IndividualPluginSelection":
            
                if name == "PluginItem":
                    self.isPluginItemElement = 1
                
                elif name == "PluginId":
                    self.isPluginItemIdElement = 1
                    self.pluginId = ""
                    
                elif name == "PluginName":
                    self.isPluginItemNameElement = 1
                    self.pluginName = ""
                
                elif name == "Family":
                    self.isPluginItemFamilyElement = 1
                    self.pluginFamily = ""
                    
                elif name == "Status":
                    self.isPluginItemStatusElement = 1
                    self.pluginStatus = ""
                        
    def characters (self, ch):
    
        # "Policies" specific data grabbers
            
        if self.isPolicyNameElement:
            self.policyName += ch
    
        if self.isPolicyCommentElement:
            self.policyComment += ch
            
        if self.isPolicyUUIDElement:
            self.policyUUID += ch
            
        if self.isPolicyPreferencesElement == 1:
            
            # "PolicyPreferences" specific data grabbers
            if self.isServerPreferenceNameElement:
                self.serverPreferenceName += ch
            
            if self.isServerPreferenceValueElement:
                self.serverPreferenceValue += ch
                
            if self.isItemFullNameElement:
                self.itemFullName += ch
            
            if self.isItemPreferenceNameElement:
                self.itemPreferenceName += ch
                
            if self.isItemPluginNameElement:
                self.itemPluginName += ch
                
            if self.isItemPreferenceTypeElement:
                self.itemPreferenceType += ch
                
            if self.isItemPreferenceValuesElement:
                self.itemPreferenceValues += ch
            
            if self.isItemSelectedValueElement:
                self.itemSelectedValue += ch
        
        #if self.isPluginSelectionElement == 1:
    
        if self.isFamilyNameElement:
                self.familyName += ch
            
        if self.isFamilyStatusElement:
                self.familyStatus += ch
                
        if self.isPluginItemIdElement:
                self.pluginId += ch
            
        if self.isPluginItemNameElement:
                self.pluginName += ch
            
        if self.isPluginItemFamilyElement:
                self.pluginFamily += ch
                
        if self.isPluginItemStatusElement:
                self.pluginStatus += ch

    def endElement(self, name):                    
    
        # Check for "Policies" end element
        if name == "Policies":
            self.isPoliciesElement = 0
            
        if name == "Policy":
            self.isPolicyElement = 0
            #self.policy['PasswordsType'] = self.passwordsType
            self.policies.append( self.policy )
            self.policy = { }
            self.policyCount += 1
            
        # If "Policies" is set look for end elements specifically in the "Policies" tree
        if self.isPolicyElement == 1 and name != "Policy":
                
            if name == "policyName":
                self.policy['PolicyName'] = self.policyName
                self.isPolicyNameElement = 0
                self.policyName = ""
                
            elif name == "policyComment":
                self.policy['PolicyComment'] = self.policyComment
                self.isPolicyCommentElement = 0
                self.policyComment = ""
                
            elif name == "uuid":
                self.policy['PolicyUUID'] = self.policyUUID
                self.isPolicyUUIDElement = 0
                self.policyUUID = ""
            
            if name == "Preferences":
                self.isPolicyPreferencesElement = 0
                
            # If "Policies" "Policy" "PolicyPreferences" is set look for end elements...
            #if self.isPolicyPreferencesElement == 1 and name != "Preferences":
            
            if name == "ServerPreferences":
                self.policy['ServerPreferences'] = self.serverPreferences
                self.isServerPreferencesElement = 0
                self.serverPreferences = { }
            
            if name == "preference":
                self.serverPreferences[self.serverPreferenceCount] = self.serverPreference
                self.isServerPreferenceElement = 0
                self.serverPreference = { }
                self.serverPreferenceCount += 1
            
            elif name == "name":
                self.serverPreference['Name'] = self.serverPreferenceName
                self.isServerPreferenceNameElement = 0
                self.serverPreferenceName = ""
                
            elif name == "value":
                self.serverPreference['Value'] = self.serverPreferenceValue
                self.isServerPreferenceValueElement = 0
                self.serverPreferenceValue = ""
                
            elif name == "PluginsPreferences":
                self.policy['PluginsPreferences'] = self.pluginsPreferences
                self.isPluginsPreferencesElement = 0
                self.pluginsPreferences = { }
            
            elif name == "item":
                self.pluginsPreferences[self.itemCount] = self.item
                self.isItemElement = 0
                self.item = { }
                self.itemCount += 1
            
            # For each "Policy" "Preferences" "PluginsPreferences" "Item" end elements......
            if self.isItemElement == 1 and name != "item":
                
                if name == "fullName":
                    self.item['FullName'] = self.itemFullName
                    self.isItemFullNameElement = 0
                    self.itemFullName = ""
                
                elif name == "preferenceName":
                    self.item['PreferenceName'] = self.itemPreferenceName
                    self.isItemPreferenceNameElement = 0
                    self.itemPreferenceName = ""
                    
                elif name == "pluginName":
                    self.item['PluginName'] = self.itemPluginName
                    self.isItemPluginNameElement = 0
                    self.itemPluginName = ""
                    
                elif name == "preferenceType":
                    self.item['PreferenceType'] = self.itemPreferenceType
                    self.isItemPreferenceTypeElement = 0
                    self.itemPreferenceType = ""
                
                elif name == "preferenceValues":
                    self.item['PreferenceValues'] = self.itemPreferenceValues
                    self.isItemPreferenceValuesElement = 0
                    self.itemPreferenceValues = ""
                
                elif name == "selectedValue":
                    self.item['SelectedValue'] = self.itemSelectedValue
                    self.isItemSelectedValueElement = 0
                    self.itemSelectedValue = ""
                
            if name == "PluginSelection":
                self.isPluginSelectionElement = 0
            
            # For each "Policy" "PluginSelection" end elements below...
            if True: #self.isPluginSelectionElement == 1 and name != "PluginSelection":
            
                if    name == "FamilySelection":
                    self.policy['FamilySelection'] = self.familySelection
                    self.isFamilySelectionElement = 0
                    self.familySelection = { }
                    
                if self.isFamilySelectionElement == 1 and name != "FamilySelection":
                
                    if name == "FamilyItem":
                        self.familySelection[self.familySelectionCount] = self.familyItem
                        self.isFamilyItemElement = 0
                        self.familyItem = { }
                        self.familySelectionCount += 1
                    
                    elif name == "FamilyName":
                        self.familyItem['FamilyName'] = self.familyName
                        self.isFamilyNameElement = 0
                        self.familyName = ""
                    
                    elif name == "Status":
                        self.familyItem['FamilyStatus'] = self.familyStatus
                        self.isFamilyStatusElement = 0
                        self.familyStatus = ""
                    
                if name == "IndividualPluginSelection":
                    self.policy['IndividualPluginSelection'] = self.individualPluginSelection
                    self.isIndividualPluginSelectionElement = 0
                    self.individualPluginSelection = { }
                
                # For each "Policy" "PluginSelection" "IndividualPluginSelection" start elements below, ...
                if self.isIndividualPluginSelectionElement == 1 and name != "IndividualPluginSelection":
                
                    if name == "PluginItem":
                        self.individualPluginSelection[self.individualPluginSelectionCount] = self.pluginItem
                        self.isPluginItemElement = 0
                        self.pluginItem = { }
                        self.individualPluginSelectionCount += 1
                    
                    elif name == "PluginId":
                        self.pluginItem['PluginID'] = self.pluginId
                        self.isPluginItemIdElement = 0
                        self.pluginId = ""
                        
                    elif name == "PluginName":
                        self.pluginItem['PluginName'] = self.pluginName
                        self.isPluginItemNameElement = 0
                        self.pluginName = ""
                    
                    elif name == "Family":
                        self.pluginItem['PluginFamily'] = self.pluginFamily
                        self.isPluginItemFamilyElement = 0
                        self.pluginFamily = ""
                        
                    elif name == "Status":
                    
                        # simple map enabled/disabled to 1/0
                        
                        if self.pluginStatus == "enabled":
                            self.pluginItem['PluginStatus'] = 1
                        
                        elif self.pluginStatus == "disabled":
                            self.pluginItem['PluginStatus'] = 0
                            
                        else: 
                            self.pluginItem = ""
                            
                        self.isPluginItemStatusElement = 0
                        self.pluginStatus = ""

#
# xml handler for reports
class NessusReportHandler(xml.sax.handler.ContentHandler):

    def __init__(self):
    
        # Report variables
        self.report = { }
        self.reportHosts = []
        
        self.isReportElement = 0
        self.isReportNameElement = 0
        self.isStartTimeElement = 0
        self.isStopTimeElement = 0
        self.isPluginSelectionElement = 0
        self.isPolicyUUIDElement = 0
        self.isReportHostElement = 0
        self.isPolicyElement = 0
        self.isTargetsElement = 0
        self.isHostProperties = 0
        
        # Report Host variables
        self.reportHost = { }
        self.reportItems = []
        
        self.reportHostCount = 0
        
        self.isReportItemElement = 0
        self.isRHHostNameElement = 0
        self.isRHStartTimeElement = 0
        self.isRHEndTimeElement = 0
        self.isRHNetbiosNameElement = 0
        self.isRHMacAddressElement = 0
        self.isRHDNSNameElement = 0
        self.isRHOSNameElement = 0
        self.isReportItemElement = 0
        self.isTag = 0
        
        # Report Item variables
        self.reportItem = { }
        
        self.reportItemCount = 0
        
        self.isRIBidElement = 0
        self.isRICveElement = 0
        self.isRICvssBaseScoreElement = 0
        self.isRICvssTemporalScoreElement = 0
        self.isRICvssTemporalVectorElement = 0
        self.isRICvssVectorElement = 0
        self.isRICweElement = 0
        self.isRIOsvdbElement = 0
        self.isRIXrefElement = 0
        self.isRIPortElement = 0
        self.isRISeverityElement = 0
        self.isRIPluginIDElement = 0
        self.isRIPluginNameElement = 0
        self.isRIPluginDataElement = 0
    
    def replaceUnknown(self, value ):
        if value is not None:
            return value.replace("(unknown)", '')
        else:
            return None
    
    def startElement(self, name, attributes):
    
        if name == "Report":
            self.isReportElement = 1
            self.report['ReportName'] = attributes.get("name")
            
        if self.isReportElement == 1 and name != "Report":
            
            if name == "ReportName":
                self.isReportNameElement = 1
                self.reportName = ""
                
            elif name == "StartTime":
                self.isStartTimeElement = 1
                self.startTime = ""
                
            elif name == "StopTime":
                self.isStopTimeElement = 1
                self.stopTime = ""
                
            elif name == "Policy":
                self.isPolicyElement = 1
                
            elif name == "Targets":
                self.isTargetsElement = 1
                
            elif name == "PluginSelection":
                self.isPluginSelectionElement = 1
                self.pluginSelection = ""
                
            elif name == "PolicyUUID":
                self.isPolicyUUIDElement = 1
                self.policyUUID = ""
            
            elif name == "ReportHost":
                self.isReportHostElement = 1
                
                if attributes.get("name") is not None:
                    self.reportHost['HostName'] = attributes.get("name")
                
            if self.isReportHostElement == 1 and name != "ReportHost":
                
                if name == "HostProperties":
                    self.isHostProperties = 1
                
                elif name == "ReportItem":
                    self.isReportItemElement = 1
                    self.reportItem['Port'] = attributes.get("svc_name") + " (" + self.replaceUnknown(attributes.get("port")) + "/" + self.replaceUnknown(attributes.get("protocol")) + ")" 
                    self.reportItem['Severity'] = self.replaceUnknown(attributes.get("severity"))
                    self.reportItem['PluginFamily'] = self.replaceUnknown(attributes.get("pluginFamily"))
                    self.reportItem['PluginID'] = self.replaceUnknown(attributes.get("pluginID"))
                    self.reportItem['PluginName'] = self.replaceUnknown(attributes.get("pluginName"))
                    #self.reportItem['ServiceName'] = self.replaceUnknown(attributes.get("svc_name"))
                    
                    if self.reportItem['PluginID'] == "0": #This is done for backwards compatibility (version 1 always includes "PORT" in the data for port findings)
                        self.reportItem['Data'] = u"PORT"
                    
                if self.isHostProperties == 1 and name == "tag":
                    self.isTag = 1
                    
                    if attributes.get("name") == "operating-system":
                        self.RHOSName = ""
                        self.isRHOSNameElement = 1
                    elif attributes.get("name") == "HOST_END":
                        self.RHEndTime = ""
                        self.isRHEndTimeElement = 1
                    elif attributes.get("name") == "mac-address":
                        self.RHMacAddress = ""
                        self.isRHMacAddressElement = 1
                    elif attributes.get("name") == "host-ip":
                        self.RHHostName = ""
                        self.isRHHostNameElement = 1
                    elif attributes.get("name") == "host-fqdn":
                        self.RHDNSName = ""
                        self.isRHDNSNameElement = 1
                    elif attributes.get("name") == "HOST_START":
                        self.RHStartTime = ""
                        self.isRHStartTimeElement = 1
                    
                if self.isReportItemElement == 1 and name != "ReportItem":

                    # Bugtraq ID reference
                    if name == "bid":
                        self.isRIBidElement = 1
                        self.RIBid = ""

                    # CVE reference
                    if name == "cve":
                        self.isRICveElement = 1
                        self.RICve = ""

                    # CVSS reference
                    if name == "cvss_base_score":
                        self.isRICvssBaseScoreElement = 1
                        self.RICvssBaseScore = ""

                    if name == "cvss_temporal_score":
                        self.isRICvssTemporalScoreElement = 1
                        self.RICvssTemporalScore = ""

                    if name == "cvss_temporal_vector":
                        self.isRICvssTemporalVectorElement = 1
                        self.RICvssTemporalVector = ""

                    if name == "cvss_vector":
                        self.isRICvssVectorElement = 1
                        self.RICvssVector = ""

                    # CWE reference
                    if name == "cwe":
                        self.isRICweElement = 1
                        self.RICwe = ""

                    # CWE reference
                    if name == "osvdb":
                        self.isRIOsvdbElement = 1
                        self.RIOsvdb = ""

                    # Other external reference
                    if name == "xref":
                        self.isRIXrefElement = 1
                        self.RIXref = ""
                
                    if name == "port":
                        self.isRIPortElement = 1
                        self.RIPort = ""
                    
                    elif name == "severity":
                        self.isRISeverityElement = 1
                        self.RISeverity = ""
                        
                    elif name == "pluginID":
                        self.isRIPluginIDElement = 1
                        self.RIPluginID = ""
                        
                    elif name == "pluginName":
                        self.isRIPluginNameElement = 1
                        self.RIPluginName = ""
                        
                    elif name == "plugin_output":
                        self.isRIPluginDataElement = 1
                        self.RIPluginData = ""
    
    def characters (self, ch):
            
        if self.isReportNameElement:
            self.reportName += ch
            
        if self.isStartTimeElement:
            self.startTime += ch
            
        if self.isStopTimeElement:
            self.stopTime += ch
            
        if self.isPluginSelectionElement:
            self.pluginSelection += ch
            
        if self.isPolicyUUIDElement:
            self.policyUUID += ch
        
        if self.isReportHostElement == 1:
            
            if self.isRHHostNameElement:
                self.RHHostName += ch
                
            if self.isRHStartTimeElement:
                self.RHStartTime += ch
                
            if self.isRHEndTimeElement:
                self.RHEndTime += ch
                
            if self.isRHNetbiosNameElement:
                self.RHNetbiosName += ch
                
            if self.isRHMacAddressElement:
                self.RHMacAddress += ch
                
            if self.isRHDNSNameElement:
                self.RHDNSName += ch
                
            if self.isRHOSNameElement:
                self.RHOSName += ch
                
            if self.isReportItemElement == 1:

                if self.isRIBidElement:
                    self.RIBid += ch

                if self.isRICveElement:
                    self.RICve += ch

                if self.isRICvssBaseScoreElement:
                    self.RICvssBaseScore += ch

                if self.isRICvssTemporalScoreElement:
                    self.RICvssTemporalScore += ch

                if self.isRICvssTemporalVectorElement:
                    self.RICvssTemporalVector += ch

                if self.isRICvssVectorElement:
                    self.RICvssVector += ch

                if self.isRICweElement:
                    self.RICwe += ch

                if self.isRIOsvdbElement:
                    self.RIOsvdb += ch

                if self.isRIXrefElement:
                    self.RIXref += ch
            
                if self.isRIPortElement:
                    self.RIPort += ch
                
                if self.isRISeverityElement:
                    self.RISeverity += ch
                    
                if self.isRIPluginIDElement:
                    self.RIPluginID += ch
                    
                if self.isRIPluginNameElement:
                    self.RIPluginName += ch
                    
                if self.isRIPluginDataElement:
                    self.RIPluginData += ch

    def endElement(self, name):
    
        if name == "Report":
            self.report['ReportHosts'] = self.reportHosts
            self.isReportElement = 0
            self.reportHosts = []
            
        if self.isReportElement == 1 and name != "Report":
            
            if name == "ReportName":
                self.report['ReportName'] = self.reportName
                self.isReportNameElement = 0
                self.reportName = ""
                
            elif name == "StartTime":
                self.report['StartTime'] = self.startTime
                self.isStartTimeElement = 0
                self.startTime = ""
                
            elif name == "StopTime":
                self.report['StopTime'] = self.stopTime
                self.isStopTimeElement = 0
                self.stopTime = ""
                
            elif name == "Policy":
                self.isPolicyElement = 0
                
            elif name == "Targets":
                self.isTargetsElement = 0
            
            # There is a "PluginSelection" element within the Policy XML object
            # Only take the "PluginSelection" from the Report XML object
            elif name == "PluginSelection" and self.isPolicyElement == 0:
                self.report['PluginSelection'] = self.pluginSelection.split(';')
                self.isPluginSelectionElement = 0
                self.pluginSelection = ""
            
            # No need to take policy uuid here (redundant with uuid in <Policy>)
            #elif name == "PolicyUUID":
            #    self.report['PolicyUUID'] = self.policyUUID
            #    self.isPolicyUUIDElement = 0
            #    self.policyUUID = ""
            
            elif name == "ReportHost":
                self.reportHost['ReportItems'] = self.reportItems
                self.reportHosts.append( self.reportHost ) 
                self.isReportHostElement = 0
                self.reportItems = []
                self.reportHost = { }
                self.reportHostCount += 1
                
            if self.isReportHostElement == 1 and name != "ReportHost":
                    
                if name == "HostProperties":
                    self.isHostProperties = 0
                    self.isRHHostNameElement = 0
                    self.isRHStartTimeElement = 0
                    self.isRHEndTimeElement = 0
                    self.isRHNetbiosNameElement = 0
                    self.isRHMacAddressElement = 0
                    self.isRHDNSNameElement = 0
                    self.isRHOSNameElement = 0
                    
                elif name == "startTime":
                    self.reportHost['StartTime'] = self.RHStartTime
                    self.isRHStartTimeElement = 0
                    self.RHStartTime = ""
                    
                elif name ==  "endTime":
                    self.reportHost['EndTime'] = self.RHEndTime
                    self.isRHEndTimeElement = 0
                    self.RHEndTime = ""
                    
                # for netbios -> os name...replace "(unknown)" with empty string
                    
                elif name == "netbios_name":
                    self.reportHost['NetbiosName'] = self.RHNetbiosName.replace("(unknown)", '')
                    self.isRHNetbiosNameElement = 0
                    self.RHNetbiosName = ""
                    
                elif name == "mac_addr":
                    self.reportHost['MacAddress'] = self.RHMacAddress.replace("(unknown)", '')
                    self.isRHMacAddressElement = 0
                    self.RHMacAddress = ""
                    
                elif name == "dns_name":
                    self.reportHost['DNSName'] = self.RHDNSName.replace("(unknown)", '')
                    self.isRHDNSNameElement = 0
                    self.RHDNSName = ""
                    
                elif name == "os_name":
                    self.reportHost['OSName'] = self.RHOSName.replace("(unknown)", '')
                    self.isRHOSNameElement = 0
                    self.RHOSName = ""
                    
                elif name == "ReportItem":
                    self.reportItems.append( self.reportItem )
                    self.isReportItemElement = 0
                    self.reportItem = { }
                    self.reportItemCount += 1
                    
                elif name == "tag":
                    self.isTag = 0
                    
                    if self.isRHOSNameElement == 1:
                        self.reportHost['OSName'] = self.RHOSName
                        
                    elif self.isRHMacAddressElement == 1:
                        macs = self.RHMacAddress
                        
                        if macs is not None:
                            macs2 = macs.split("\n")
                            macs = []
                            
                            for m in macs2:
                                if len(m.strip()) > 0:
                                    macs.append(m)
                                    
                            if len(macs) >= 0:
                                self.reportHost['MacAddresses'] = macs
                                self.reportHost['MacAddress'] = macs[0] # Save only the first MAC into the MacAddress field (for backward compatibility)
                        
                    elif self.isRHDNSNameElement == 1: # Split MAC address
                        self.reportHost['DNSName'] = self.RHDNSName
                        
                    elif self.isRHHostNameElement == 1:
                        self.reportHost['HostName'] = self.RHHostName
                        
                    elif self.isRHStartTimeElement == 1:
                        self.reportHost['StartTime'] = self.RHStartTime
                        
                    elif self.isRHEndTimeElement == 1:
                        self.reportHost['EndTime'] = self.RHEndTime
                    
                    self.isRHHostNameElement = 0
                    self.isRHStartTimeElement = 0
                    self.isRHEndTimeElement = 0
                    self.isRHNetbiosNameElement = 0
                    self.isRHMacAddressElement = 0
                    self.isRHDNSNameElement = 0
                    self.isRHOSNameElement = 0
                    
                if self.isReportItemElement == 1 and name != "ReportItem":

                    if name == "bid":
                        if self.reportItem.get('bid', False):
                            self.reportItem['bid'] += ' %s' % self.RIBid
                        else:
                            self.reportItem['bid'] = self.RIBid
                        self.isRIBidElement = 0
                        self.RIBid = ""

                    elif name == "cve":
                        if self.reportItem.get('cve', False):
                            self.reportItem['cve'] += ' %s' % self.RICve
                        else:
                            self.reportItem['cve'] = self.RICve
                        self.isRICveElement = 0
                        self.RICve = ""

                    elif name == "cwe":
                        if self.reportItem.get('cwe', False):
                            self.reportItem['cwe'] += ' %s' % self.RICwe
                        else:
                            self.reportItem['cwe'] = self.RICwe
                        self.isRICweElement = 0
                        self.RICwe = ""

                    elif name == "osvdb":
                        if self.reportItem.get('osvdb', False):
                            self.reportItem['osvdb'] += ' %s' % self.RIOsvdb
                        else:
                            self.reportItem['osvdb'] = self.RIOsvdb
                        self.isRIOsvdbElement = 0
                        self.RIOsvdb = ""

                    elif name == "xref":
                        if self.reportItem.get('xref', False):
                            self.reportItem['xref'] += ' %s' % self.RIXref
                        else:
                            self.reportItem['xref'] = self.RIXref
                        self.isRIXrefElement = 0
                        self.RIXref = ""

                    elif name == "cvss_base_score":
                        self.reportItem['CvssBaseScore'] = self.RICvssBaseScore
                        self.isRICvssBaseScoreElement = 0
                        self.RICvssBaseScore = ""

                    elif name == "cvss_temporal_score":
                        self.reportItem['CvssTemporalScore'] = self.RICvssTemporalScore
                        self.isRICvssTemporalScoreElement = 0
                        self.RICvssTemporalScore = ""

                    elif name == "cvss_temporal_vector":
                        self.reportItem['CvssTemporalVector'] = self.RICvssTemporalVector
                        self.isRICvssTemporalVectorElement = 0
                        self.RICvssTemporalVector = ""

                    elif name == "cvss_vector":
                        self.reportItem['CvssVector'] = self.RICvssVector
                        self.isRICvssVectorElement = 0
                        self.RICvssVector = ""
                
                    elif name == "port":
                        self.reportItem['Port'] = self.RIPort
                        self.isRIPortElement = 0
                        self.RIPort = ""
                    
                    elif name == "severity":
                        self.reportItem['Severity'] = self.RISeverity
                        self.isRISeverityElement = 0
                        self.RISeverity = ""
                        
                    elif name == "pluginID":
                        self.reportItem['PluginID'] = self.RIPluginID
                        self.isRIPluginIDElement = 0
                        self.RIPluginID = ""
                        
                    elif name == "pluginName":
                        self.reportItem['PluginName'] = self.RIPluginName
                        self.isRIPluginNameElement = 0
                        self.RIPluginName = ""
                        
                    elif name == "plugin_output":
                        self.reportItem['Data'] = self.RIPluginData
                        self.isRIPluginDataElement = 0
                        self.RIPluginData = ""