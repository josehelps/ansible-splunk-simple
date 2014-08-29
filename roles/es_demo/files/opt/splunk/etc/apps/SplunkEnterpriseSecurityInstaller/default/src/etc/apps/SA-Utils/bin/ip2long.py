'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import csv
import re
import sys

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.ipMath import LongToIP, IPToLong

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)


if __name__ == '__main__':
    
    ipRex = re.compile('^(([0-1]\d{0,2}|2[0-4]\d|25[0-5]|\d{0,2})\.){3}([0-1]\d{0,2}|2[0-4]\d|25[0-5]|\d{0,2})$')
                    
    ## Retrieve input
    inputResults = csv.reader(sys.stdin, lineterminator='\n')
    
    header = inputResults.next()
    
    ## Initialize output handlers
    csv.writer(sys.stdout, lineterminator='\n').writerow(header)
    output = csv.DictWriter(sys.stdout, header, lineterminator='\n', restval='')

    longKey = header.index('long')
    ipKey = header.index('ip')
        
    for inputResult in inputResults:
        ## Initialize and populate output lists/dictionary
        outputResult = {}
                
        if len(inputResult[longKey]) > 0:
            outputResult['long'] = inputResult[longKey]
                   
            try:
                longVal = long(inputResult[longKey])
                        
                if longVal >= 0 and longVal <= 4294967295:
                    outputResult['ip'] = LongToIP(longVal)   
                        
            except:
                pass
                
        ## The reverse lookup
        else:
            outputResult['ip'] = inputResult[ipKey]
                
            if ipRex.match(inputResult[ipKey]):
                outputResult['long'] = IPToLong(inputResult[ipKey])
            
        output.writerow(outputResult)