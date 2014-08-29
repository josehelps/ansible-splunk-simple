'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import csv
import os
import sys

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)
  
if __name__ == '__main__':
    ## Retrieve input
    ## This is done here in case we need to return
    inputData = csv.reader(sys.stdin)

    ## Process the first result as the header
    ## Also as an indication to initialize output handlers
    header = inputData.next()
    csv.writer(sys.stdout, lineterminator='\n').writerow(header)
    # The "header" option is required to set the ordering of output fields. 
    output = csv.DictWriter(sys.stdout, header, lineterminator='\n')

    for inputResult in inputData:
        outputResult = dict(zip(header,inputResult))            
        inputKey = outputResult.get('input','')
        if len(inputKey) > 0:
            # Exclude empty strings in case "split" returns any.
            for val in filter(lambda x: len(x) > 0, set(inputKey.split('|'))):
                outputResult['output'] = val
                output.writerow(outputResult)

        else:
            sys.stdout.write('-1')