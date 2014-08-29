'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import csv
import os
import re
import sys

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

## This Python function implements the algorithm described above, returning True if the given input 
## represents a valid Luhn number, and False otherwise. It expects the input as (1) a string of 
## digits, or (2) an array of digits, each of which must be an integer 0<=n<=9. It reverses the 
## digits, and it uses a boolean alternator.
def check_number(digits):
    _sum = 0
    alt = False
    
    for d in reversed(digits):
        d = int(d)
        assert 0 <= d <= 9
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        _sum += d
        alt = not alt
    return (_sum % 10) == 0

    
if __name__ == '__main__':
    
    maxStrength = 19
        
    ## Override Defaults w/ opts below
    if len(sys.argv) > 1:
        for a in sys.argv:
            if a.startswith("maxStrength="):
                where = a.find('=')
                maxStrength = a[where+1:len(a)]
                
    header = []
    outputResults = []
    inputResults = csv.reader(sys.stdin, lineterminator='\n')

    header = inputResults.next()
    csv.writer(sys.stdout, lineterminator='\n').writerow(header)
    outputResults = csv.DictWriter(sys.stdout, header, lineterminator='\n')
        
    for inputResult in inputResults:

        outputResult = {}
        forwardLookup = False
        
        for x in range(0,len(inputResult)):
            outputResult[header[x]] = inputResult[x]
    
        if outputResult.has_key(header[0]) and len(outputResult[header[0]]) > 0:
            forwardLookup = True
            
            val = outputResult[header[0]]
                
            digits = re.sub('[^0-9]', '', val)
            digits = re.sub('[0]{' + str(len(digits)) + '}', '', digits)
                        
            if len(digits) > 0 and len(digits) <= maxStrength:
                if check_number(digits):
                    outputResult[header[1]] = val
                    outputResult[header[2]] = digits
        
        if forwardLookup:
            outputResults.writerow(outputResult)
            
        else:
            ## This script does not support reverse lookups
            ## Output "-1" when a reverse lookup is attempted
            ## This is supported in 4.2+ as an alternative to csv.QUOTE_ALL
            sys.stdout.write('-1\n')