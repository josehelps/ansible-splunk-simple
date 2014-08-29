'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''

import xml.sax.handler
import re
import ipmath
import pprint

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
        
        # Report Host variables
        self.reportHost = { }
        self.reportItems = []
        
        self.reportHostCount = 0
        
        self.isReportItemElement = 0
        self.isRHHostNameElement = 0
        self.isRHStartTimeElement = 0
        self.isRHStopTimeElement = 0
        self.isRHNetbiosNameElement = 0
        self.isRHMacAddressElement = 0
        self.isRHDNSNameElement = 0
        self.isRHOSNameElement = 0
        self.isRHNumPortsElement = 0
        self.isRHNumLoElement = 0
        self.isRHNumMedElement = 0
        self.isRHNumHiElement = 0
        self.isReportItemElement = 0
        
        # Report Item variables
        self.reportItem = { }
        
        self.reportItemCount = 0

        self.isRIPortElement = 0
        self.isRISeverityElement = 0
        self.isRIPluginIDElement = 0
        self.isRIPluginNameElement = 0
        self.isRIPluginDataElement = 0
    
    def startElement(self, name, attributes):
    
        if name == "Report":
            self.isReportElement = 1
            
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
                
            #elif name == "PluginSelection":
            #    self.isPluginSelectionElement = 1
            #    self.pluginSelection = ""
                
            elif name == "PolicyUUID":
                self.isPolicyUUIDElement = 1
                self.policyUUID = ""
            
            elif name == "ReportHost":
                self.isReportHostElement = 1
                
            if self.isReportHostElement == 1 and name != "ReportHost":
                
                if name == "HostName":
                    self.isRHHostNameElement = 1
                    self.RHHostName = ""
                    
                elif name == "startTime":
                    self.isRHStartTimeElement = 1
                    self.RHStartTime = ""
                    
                elif name ==  "stopTime":
                    self.isRHStopTimeElement = 1
                    self.RHStopTime = ""
                    
                elif name == "netbios_name":
                    self.isRHNetbiosNameElement = 1
                    self.RHNetbiosName = ""
                    
                elif name == "mac_addr":
                    self.isRHMacAddressElement = 1
                    self.RHMacAddress = ""
                    
                elif name == "dns_name":
                    self.isRHDNSNameElement = 1
                    self.RHDNSName = ""
                    
                elif name == "os_name":
                    self.isRHOSNameElement = 1
                    self.RHOSName = ""
                    
                elif name == "num_ports":
                    self.isRHNumPortsElement = 1
                    self.RHNumPorts = ""
                    
                elif name == "num_lo":
                    self.isRHNumLoElement = 1
                    self.RHNumLo = ""
                    
                elif name == "num_med":
                    self.isRHNumMedElement = 1
                    self.RHNumMed = ""
                    
                elif name == "num_hi":
                    self.isRHNumHiElement = 1
                    self.RHNumHi = ""
                    
                elif name == "ReportItem":
                    self.isReportItemElement = 1
                    
                if self.isReportItemElement == 1 and name != "ReportItem":
                
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
                        
                    elif name == "data":
                        self.isRIPluginDataElement = 1
                        self.RIPluginData = ""
    
    def characters (self, ch):
            
        if self.isReportNameElement:
            self.reportName += ch
            
        if self.isStartTimeElement:
            self.startTime += ch
            
        if self.isStopTimeElement:
            self.stopTime += ch
            
        #if self.isPluginSelectionElement:
        #    self.pluginSelection += ch
            
        if self.isPolicyUUIDElement:
            self.policyUUID += ch
        
        if self.isReportHostElement == 1:
            
            if self.isRHHostNameElement:
                self.RHHostName += ch
                
            if self.isRHStartTimeElement:
                self.RHStartTime += ch
                
            if self.isRHStopTimeElement:
                self.RHStopTime += ch
                
            if self.isRHNetbiosNameElement:
                self.RHNetbiosName += ch
                
            if self.isRHMacAddressElement:
                self.RHMacAddress += ch
                
            if self.isRHDNSNameElement:
                self.RHDNSName += ch
                
            if self.isRHOSNameElement:
                self.RHOSName += ch
                
            if self.isRHNumPortsElement:
                self.RHNumPorts += ch
                
            if self.isRHNumLoElement:
                self.RHNumLo += ch
                
            if self.isRHNumMedElement:
                self.RHNumMed += ch
                
            if self.isRHNumHiElement:
                self.RHNumHi += ch
                
            if self.isReportItemElement == 1:

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
            #elif name == "PluginSelection" and self.isPolicyElement == 0:
            #    self.report['PluginSelection'] = self.pluginSelection.split(';')
            #    self.isPluginSelectionElement = 0
            #    self.pluginSelection = ""
            
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
                
                if name == "HostName":
                    self.reportHost['HostName'] = self.RHHostName
                    self.isRHHostNameElement = 0
                    self.RHHostName = ""
                    
                elif name == "startTime":
                    self.reportHost['StartTime'] = self.RHStartTime
                    self.isRHStartTimeElement = 0
                    self.RHStartTime = ""
                    
                elif name ==  "stopTime":
                    self.reportHost['EndTime'] = self.RHStopTime
                    self.isRHStopTimeElement = 0
                    self.RHStopTime = ""
                    
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
                    
                elif name == "num_ports":
                    self.reportHost['NumPorts'] = self.RHNumPorts
                    self.isRHNumPortsElement = 0
                    self.RHNumPorts = ""
                    
                elif name == "num_lo":
                    self.reportHost['NumLo'] = self.RHNumLo
                    self.isRHNumLoElement = 0
                    self.RHNumLo = ""
                    
                elif name == "num_med":
                    self.reportHost['NumMed'] = self.RHNumMed
                    self.isRHNumMedElement = 0
                    self.RHNumMed = ""
                    
                elif name == "num_hi":
                    self.reportHost['NumHi'] = self.RHNumHi
                    self.isRHNumHiElement = 0
                    self.RHNumHi = ""
                    
                elif name == "ReportItem":
                    self.reportItems.append( self.reportItem )
                    self.isReportItemElement = 0
                    self.reportItem = { }
                    self.reportItemCount += 1
                    
                if self.isReportItemElement == 1 and name != "ReportItem":
                
                    if name == "port":
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
                        
                    elif name == "data":
                        #self.reportItem['Data'] = self.RIPluginData
                        bidRx = re.compile('BID\s*:\s*(\d+)')                                                                                                                                                                       
                        cveRx = re.compile('((?:CVE|CAN)-\d+-\d+)')                                                                                                                                                                 
                        cvssScoreRx = re.compile('CVSS Base Score\s*:\s*(\d+\.\d+)')                                                                                                                                                    
                        cvssVectorRx = re.compile('\((CVSS2[^\)]+)\)')                                                                                                                                                              
                        cweRx = re.compile('CWE\s*:\s*(\d+)')                                                                                                                                                                       
                        osvdbRx = re.compile('OSVDB\s*:\s*(\d+)')                                                                                                                                                                   
                        xrefRx = re.compile('Other references\s*:\s*(.*)\\\\n')   

                        bidMatches = bidRx.findall(self.RIPluginData)
                        cveMatches = cveRx.findall(self.RIPluginData)
                        cvssScoreMatches = cvssScoreRx.findall(self.RIPluginData)
                        cvssVectorMatches = cvssVectorRx.findall(self.RIPluginData)
                        cweMatches = cweRx.findall(self.RIPluginData)
                        osvdbMatches = osvdbRx.findall(self.RIPluginData)
                        xrefMatches = xrefRx.findall(self.RIPluginData)
                        
                        if bidMatches:
                            self.reportItem['bid'] = ' '.join(bidMatches)

                        if cveMatches:
                            self.reportItem['cve'] = ' '.join(cveMatches)

                        # CVSS score and vector are actually single-valued, so join with empty string.
                        if cvssScoreMatches:
                            self.reportItem['CvssBaseScore'] = ''.join(cvssScoreMatches)

                        if cvssVectorMatches:
                            self.reportItem['CvssVector'] = ''.join(cvssVectorMatches)

                        if cweMatches:
                            self.reportItem['cwe'] = ' '.join(cweMatches)

                        if osvdbMatches:
                            self.reportItem['osvdb'] = ' '.join(osvdbMatches)

                        if xrefMatches:
                            # Xref requires special handling as it will return 
                            # a comma-separated string of external references.
                            self.reportItem['xref'] = ' '.join(xrefMatches[0].split(','))
                        
                        self.isRIPluginDataElement = 0
                        self.RIPluginData = ""
