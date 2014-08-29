'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import csv
import os
import re
import string
import sys

import IP2Location

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5)
if sys.version_info[0] >= 2 and sys.version_info[1] >= 5:
    csv.field_size_limit(10485760)

# Defaults
app = 'TA-ip2location'
file = 'IP-COUNTRY-SAMPLE.BIN'
IP2LocObj = IP2Location.IP2Location()

# Function to exclude text from output field.
# This text is usually an artifact of the API when running unlicensed.
# We could do this with a lambda but it would not work on Python 2.6.8,
# which is sometimes the version this script ends up running on.
def normalize(val):
    exclusion_text = 'This parameter is unavailable for selected data file. Please upgrade the data file.'
    retval = val
    if isinstance(retval, basestring):
        retval = string.replace(retval,exclusion_text, '')
    return retval

## Override Defaults w/ opts below
if len(sys.argv) > 1:
    for a in sys.argv:
        if a.startswith('app='):
            where = a.find('=')
            app = a[where+1:len(a)]
        elif a.startswith('file='):
            where = a.find('=')
            file = a[where+1:len(a)]
            
# 1 -- Get the full file path and open the file
grandparent = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) 
ip2locationFile = os.path.join(grandparent, app, 'lookups', file)

try:
    IP2LocObj.open(ip2locationFile)
except:
    print 'Error; Cannot open ' + ip2locationFile
    exit()

ipRex = re.compile('^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$')    

## Define allowed fields
api_fields_list = ['area_code', 'city', 'country_short', 'country_long', 'domain',
            'idd_code', 'isp', 'latitude', 'longitude', 'mcc', 'mnc',
            'mobile_brand', 'netspeed', 'region', 'timezone', 'weather_code',
            'weather_name', 'zipcode']

## Get The Input
inputResults = csv.reader(sys.stdin, lineterminator='\n')
header = inputResults.next()
key = header[0]

## Initialize output
csv.writer(sys.stdout,lineterminator='\n').writerow(header)
outputResults = csv.DictWriter(sys.stdout,header,lineterminator='\n')
outputResultsQA = csv.DictWriter(sys.stdout,header,quoting=csv.QUOTE_ALL,lineterminator='\n')

## Iterate Results "List of Dicts"
for inputResult in inputResults:

    outputResult = {}
    forwardLookup = False
    location = False
    
    for x in range(0,len(inputResult)):
        outputResult[header[x]] = inputResult[x]
    
    if outputResult.has_key(key) and len(outputResult[key]) > 0:
        forwardLookup = True
        
        if ipRex.match(outputResult[key]):
            location = IP2LocObj.get_all(outputResult[key]);

    if forwardLookup:
        if location:
            # Output only the requested fields.
            # Use old "dict" function instead of dictionary comprehensions
            # to ensure Python 2.4.3 compatibility, since that's the default
            # on some versions of CentOS.
            field_map = dict([s, string.replace(s, key + '_', '')] for s in outputResult.keys())
            reverse_field_map = dict([string.replace(s, key + '_', ''), s] for s in outputResult.keys())

            for outfield, locfield in field_map.items():
               if locfield in api_fields_list:
                   outputResult[outfield] = normalize(getattr(location, locfield, None))
                   
            # Set the latitude and longitude to null if both are 0.0;
            # this indicates a failed lookup.
            if outputResult[reverse_field_map['latitude']] == 0.0 and outputResult[reverse_field_map['longitude']] == 0.0:
                outputResult[reverse_field_map['latitude']] = None
                outputResult[reverse_field_map['longitude']] = None

        outputResults.writerow(outputResult)
        
    else:
        outputResultsQA.writerow(outputResult)
