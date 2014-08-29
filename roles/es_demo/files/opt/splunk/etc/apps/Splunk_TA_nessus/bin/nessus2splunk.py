'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
# Native Imports
import argparse
import hashlib
import lxml
import lxml.etree
import operator
import os
import re
import shutil 
import string
import sys
import textwrap
import xml.sax

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# Custom Imports
import nessusclienthandler
import nessusclienthandler2  # Used for the version 2 of the Nessus file parser


class PathType(object):
    '''Class for use as an argument type in an ArgumentParser.
    The __call__ function will validate whether the directory passed as the
    argument exists.
    '''

    def __call__(self, val):
        '''Returns a correctly formatted path for the current version of the OS.
        If the path does not exist or is not readable, raises ArgumentTypeError.
        '''
        val = os.path.normpath(val)
        if os.path.isdir(val):
            return val
        else:
            raise argparse.ArgumentTypeError("Invalid path specified ($SPLUNK_HOME may not be set).")


def GetOptions(argv=None):

    desc = '''
    Script for converting Nessus v1 and v2 reports into Splunk-compatible format.
            
    Intended to be run as a scripted input via inputs.conf.
        
    Example of use in inputs.conf:
    
        [script://./bin/nessus2splunk.py]
        disabled = false
        interval = 120
        index = _internal
        source = nessus2splunk
        sourcetype = nessus2splunk

    Example of use in inputs.conf using custom source and target directories
    for input and output files:
    
        [script://./bin/nessus2splunk.py -s /opt/nessus/incoming -t /opt/nessus/parsed]
        disabled = false
        interval = 120
        index = _internal
        source = nessus2splunk
        sourcetype = nessus2splunk
    
    Both srcdir and tgtdir arguments must be either:
    
    - Fully qualified paths from the root directory, OR
    - A relative path, relative to the app directory.
        
    Note that if the target directory is different from $SPLUNK_HOME/var/spool/splunk,
    it is necessary to set up a "monitor" stanza in inputs.conf referring to the target
    directory. Additionally, the target directory must already exist on the filesystem.
    '''

    parser = argparse.ArgumentParser(description=textwrap.dedent(desc),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Set the default directory for input files.    
    grandparent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    input_default = os.path.join(grandparent, 'Splunk_TA_nessus', 'spool')

    # Set the default directory for output files.
    output_default = make_splunkhome_path(['var', 'spool', 'splunk'])

    parser.add_argument('-s', '--srcdir',
        dest='srcdir',
        type=PathType(),
        action='store',
        help='The source directory for locating Nessus data files.',
        default=input_default)

    parser.add_argument('-t', '--tgtdir',
        dest='tgtdir',
        type=PathType(),
        action='store',
        help='The target directory for placing converted Nessus output.',
        default=output_default)
    
    return parser.parse_args(argv)


def ParseReport(filePath):
    # Open the nessus file
    nessusFile = open(filePath, 'r')

    # Read entire file into list
    nessusFileList = nessusFile.readlines()
    nessusFileXML = string.join(nessusFileList, '')
    #print nessusFileXML
        
    nessusFile.close()

    if DetermineVersion(nessusFileXML) == 2:
        return ParseReportXMLver2(nessusFileXML, filePath)
    else:
        return ParseReportXMLver1(nessusFileXML, filePath)


def DetermineVersion(nessusFileXML):
    v2Regx = re.compile('\<NessusClientData_v2\>')
    
    if v2Regx.search(nessusFileXML) is not None:
        return 2
    else:
        return 1
    
    
def ParseReportXMLver2(reportXMLString, filePath=None):
    # Hash File
    h = hashlib.sha1()
    h.update(reportXMLString)
    hashval = h.hexdigest()
    
    # Note: We are not parsing the Targets or Policies sections at the top level
    # Instead we are parsing the Targets and Policy objects (subsections) within the top level report section
    # We could parse these sections with additional code if necessary
    
    # Parse Report
    reportParser = xml.sax.make_parser()
    reportHandler = nessusclienthandler2.NessusReportHandler()
    reportParser.setContentHandler(reportHandler)
    xml.sax.parseString(reportXMLString, reportHandler)
    #pprint.pprint(reportHandler.report)
    report = reportHandler.report

    # Parse Report Policy 
    policyParser = xml.sax.make_parser()
    policyHandler = nessusclienthandler2.NessusPoliciesHandler()
    policyParser.setContentHandler(policyHandler)
    xml.sax.parseString(reportXMLString, policyHandler)
    #pprint.pprint(policyHandler.policies)
    report['Policy'] = policyHandler.policies
    
    if filePath is not None:
        report['FileName'] = filePath
    
    report['FileHash'] = hashval
    
    # Populate the PluginSelection
    for i in report['Policy'][0]['ServerPreferences']:
        if report['Policy'][0]['ServerPreferences'][i]['Name'] == 'plugin_set':
            report['PluginSelection'] = report['Policy'][0]['ServerPreferences'][i]['Value'].split(";")
    
    # Populate the report name
    #report['ReportName'] = report['ReportHosts'][0]
    
    # Populate StartTime, EndTime
    if len(report['ReportHosts']) > 0:
        report['StartTime'] = report['ReportHosts'][0]['StartTime']
        report['StopTime'] = report['ReportHosts'][-1]['EndTime']
    
    # Parse Report Targets
    import ipmath
    targets = []
    
    for i in report['Policy'][0]['ServerPreferences']:
        if report['Policy'][0]['ServerPreferences'][i]['Name'] == 'TARGET':
            target = report['Policy'][0]['ServerPreferences'][i]['Value'].split(",")
            ipRegex = re.compile('\d+\.\d+\.\d+\.\d+')
            netRegex = re.compile('(\d+\.\d+\.\d+\.\d+/\d+)')
            rangeRegex = re.compile('\d+\.\d+\.\d+\.\d+\-\d+\.\d+\.\d+\.\d+')
            
            for t in target:
                if len(t.strip()) > 0:
                    entry = {}
                    ipMatch = ipRegex.match(t)
                    netMatch = netRegex.match(t)
                    rangeMatch = rangeRegex.match(t)
                    
                    #If a range
                    ipRange = t.split("-")
                    
                    if len(ipRange) >= 2 and rangeMatch:
                        entry['StartAddress'] = ipmath.IPToLong(ipRange[0])
                        entry['EndAddress'] = ipmath.IPToLong(ipRange[1])
                        entry['Type'] = 'range'
                        
                    #If a netmasked range
                    elif netMatch:
                        tempRange = ipmath.CIDRToRange(netMatch.group(1))
                        entry['StartAddress'] = ipmath.IPToLong(tempRange['startAddress'])
                        entry['EndAddress'] = ipmath.IPToLong(tempRange['endAddress'])
                        entry['Type'] = "range"
                        
                    #If an IP
                    elif ipMatch:
                        entry['StartAddress'] = ipmath.IPToLong(ipMatch.group())
                        entry['EndAddress'] = ipmath.IPToLong(ipMatch.group())
                        entry['Type'] = "ip"
                        
                    #If a host name
                    else:
                        entry['Hostname'] = t
                    
                    entry['Selected'] = "1"
                    
                    targets.append(entry)
    
    report['Targets'] = targets
    
    # Return reports
    return [report]
    
    
def ParseReportXMLver1(nessusFileXML, filePath=None):
    # It is important to split the nessus file into it's 3 sections (Targets, Policies, Report)
    # Nessus adds complication by also placing a "Targets" and "Policy" (not Policies) object within the Report section
    
    # Declaring report section variables here:
    reportXML = {}              # dictionary containing multiple report xml data
    reports = []                # dictionary containing multiple parsed reports

    reportStartIndex = {}       # dictionary for start index
    reportStartCount = 0        # counter for start indexes dictionary entries

    reportEndIndex = {}         # dictionary for end index
    reportEndCount = 0          # counter for end index dictionary entries
    
    # Hash File - unused (why?)
    #h = hashlib.md5()
    #h.update(nessusFileXML)
    #hashval = h.hexdigest()

    # Discover where report sections begin
    reportStartRegx = re.compile('\<Report\>')
    reportStartIterator = reportStartRegx.finditer(nessusFileXML)

    if reportStartIterator:
        
        for match in reportStartIterator:
            
            tempSpan = match.span()
            reportStartIndex[reportStartCount] = tempSpan[0]
            reportStartCount += 1
    
    # Discover where report sections end
    reportEndRegx = re.compile('\<\/Report\>')
    reportEndIterator = reportEndRegx.finditer(nessusFileXML)

    if reportEndIterator:
        
        for match in reportEndIterator:
            
            tempSpan = match.span()
            reportEndIndex[reportEndCount] = tempSpan[1]
            reportEndCount += 1

    # Populate reportXML dictionary with XML from each report
    for x in range(0, reportStartCount):

        reportXML = nessusFileXML[reportStartIndex[x]:reportEndIndex[x]]

        # Note: We are not parsing the Targets or Policies sections at the top level
        # Instead we are parsing the Targets and Policy objects (subsections) within the top level report section
        # We could parse these sections with additional code if necessary
        
        # Parse Report
        reportParser = xml.sax.make_parser()
        reportHandler = nessusclienthandler.NessusReportHandler()
        reportParser.setContentHandler(reportHandler)
        xml.sax.parseString(reportXML, reportHandler)
        #pprint.pprint(reportHandler.report)
        reports.append(reportHandler.report)

        # Parse Report Targets
        #targetsParser = xml.sax.make_parser()
        #targetsHandler = nessusclienthandler.NessusTargetsHandler()
        #targetsParser.setContentHandler(targetsHandler)
        #xml.sax.parseString(reportXMLString, targetsHandler)
        #pprint.pprint(targetsHandler.targets)
        #reports['Targets'] = targetsHandler.targets

        # Parse Report Policy 
        #policyParser = xml.sax.make_parser()
        #policyHandler = nessusclienthandler.NessusPoliciesHandler()
        #policyParser.setContentHandler(policyHandler)
        #xml.sax.parseString(reportXMLString, policyHandler)
        #pprint.pprint(policyHandler.policies)
        #reports['Policy'] = policyHandler.policies
        
        #if filePath is not None:
        #    reports['FileName'] = filePath
        
        #reports['FileHash'] = hash
        
    # Return reports
    return reports


def GetFields():
    '''Return the set of single-valued report field mappings as a list of 
    tuples (field, key, mapping function, isRequired).'''
    return [('start_time', 'StartTime', str, True),
            ('end_time', 'EndTime', str, True),
            ('dest_dns', 'DNSName', lambda x: str(x).strip('\.'), False),
            ('dest_nt_host', 'NetbiosName', str, False),
            ('dest_mac', 'MacAddress', str, False),
            ('dest_ip', 'HostName', str, False),
            ('os', 'OSName', lambda x: [i.group(1) for i in re.finditer('([^\r\n]+)', x)], False)
        ]


def GetSubFields():
    '''Return the set of single-valued subreport field mappings as a list of tuples (field, key, mapping function).'''
    
    # operator.methodcaller is used here so that any string will be handled;
    # str.split and unicode.split work on only one type of string.
    return [('cvss_base_score', 'CvssBaseScore', str),
            ('cvss_temporal_score', 'CvssTemporalScore', str),
            ('cvss_temporal_vector', 'CvssTemporalVector', str),
            ('cvss_vector', 'CvssVector', str),
            ('dest_port_proto', 'Port', str),
            ('severity_id', 'Severity', str),
            ('signature_family', 'PluginFamily', str),
            ('signature_id', 'PluginID', str),
            ('signature', 'PluginName', str),
            ('bid', 'bid', operator.methodcaller('split')),
            ('cve', 'cve', operator.methodcaller('split')),
            ('cwe', 'cwe', operator.methodcaller('split')),
            ('osvdb', 'osvdb', operator.methodcaller('split')),
            ('xref', 'xref', operator.methodcaller('split'))
        ]


if __name__ == '__main__':
    
    # Custom LINE_BREAKER string
    LINE_BREAKER = "\r\n---splunk-ta-nessus-end-of-event---\r\n"
    
    # Maintain count of successfully processed .nessus files.
    processed = 0

    # lxml parser used for validation.
    parser = lxml.etree.XMLParser()

    # Retrieve command-line options
    options = GetOptions(sys.argv[1:])
    
    # Retrieve field transformations
    #fields = GetFields()

    # Iterate over all .nessus files. 
    for nessusFile in os.listdir(options.srcdir):
        
        # Input file path.
        nessusFilePath = os.path.join(options.srcdir, nessusFile)
        
        # Temporary output file.
        splunkFile = nessusFilePath + '.splunk'
        
        if nessusFile.endswith('.nessus'):
            print 'Processing file ' + nessusFilePath
            
            # Validate the XML
            with open(nessusFilePath, 'r') as fh:
                try:
                    tree = lxml.etree.parse(fh, parser)
                except lxml.etree.XMLSyntaxError as e:
                    # Invalid XML; proceed with next file.
                    print 'Error; input file was not valid XML: %s' % nessusFilePath
                    continue
                except Exception as e:
                    print 'Error; unknown error while parsing XML file %s: (Exception: %s)' % (nessusFilePath, e)

            theReports = ParseReport(nessusFilePath)
            
            # Increment count.
            processed += 1

            with open(splunkFile, 'w') as splunkFH:
                print "\tCreating temporary Splunk Nessus file: " + splunkFile
            
                for a in range(0, len(theReports)):
                    reportHosts = theReports[a]['ReportHosts']
                            
                    for reportHost in reportHosts:
                        reportItems = reportHost.get('ReportItems', [])
                        event = ''
                        subevent = ''
    
                        for field, key, mapper, isRequired in GetFields():
                            if len(reportHost.get(key, '')) > 0:
                                value = mapper(reportHost[key])
                                if isinstance(value, list):
                                    for v in value:
                                        event += ' %s="%s"' % (field, v)
                                elif isinstance(value, basestring):
                                    event += ' %s="%s"' % (field, value)
                                else:
                                    # Unknown mapping error.
                                    print "Error; value for field could not be mapped: %s" % field
                            else:
                                # Field value is null.
                                if isRequired:
                                    # Add a blank value
                                    event += ' %s="%s"' % (field, '')
                                else:
                                    # Field did not exist in data but is not required; ignore.
                                    pass


                        for reportItem in reportItems:
                            subevent = ''
                                
                            for field, key, mapper in GetSubFields():
                                if len(reportItem.get(key, '')) > 0:
                                    value = mapper(reportItem[key])
                                    if isinstance(value, list):
                                        for v in value:
                                            subevent += ' %s="%s"' % (field, v)
                                    elif isinstance(value, basestring):
                                        subevent += ' %s="%s"' % (field, value)
                                    else:
                                        # Unknown mapping error.
                                        print "Error; value for field could not be mapped: %s" % field

                            # Write the event. Note that if a host has no
                            # reportItems, it will not be output.
                            # LINE_BREAKER includes its own newlines, no need to add them here.
                            splunkFH.write(LINE_BREAKER + event.strip() + ' ' + subevent.strip())

            if os.path.isfile(splunkFile):
                
                # Move the output file to the target directory.
                try:
                    shutil.move(splunkFile, os.path.join(options.tgtdir, nessusFile))
                    print "\tMoving Splunk Nessus file to spool file: " + os.path.join(options.tgtdir, nessusFile)

                    # Remove the original file.
                    try:
                        os.remove(nessusFilePath)
                    except Exception as detail:
                        print 'Error; Could not delete original file from Nessus spool directory: ' + str(detail)

                except Exception as detail:
                    print 'Error; Could not move file from Nessus spool to Splunk spool: ' + str(detail)

            else:
                print 'Error; Could not create temporary file for processing Nessus input: ' + splunkFile
                
        else:
            # This file was not a .nessus file. Do not warn since this is acceptable.
            pass

    # End for loop
    if processed == 0:
        #print 'Warning; no files in .nessus format were found in the source directory: %s' % options.srcdir
        pass
