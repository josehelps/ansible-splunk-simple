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
        
def Priority2Int(priorityString):
    
    if priorityString.lower() == 'critical':
        return 5
    
    elif priorityString.lower() == 'high':
        return 4
        
    elif priorityString.lower() == 'medium':
        return 3
        
    elif priorityString.lower() == 'low':
        return 2
    
    elif priorityString.lower() == 'informational':
        return 1
        
    else:
        return 0
        
def Int2Priority(priorityInt):
    
    if priorityInt == 5:
        return "critical"
        
    elif priorityInt == 4:
        return "high"
        
    elif priorityInt == 3:
        return "medium"
        
    elif priorityInt == 2:
        return "low"
    
    elif priorityInt == 1:
        return "informational"
        
    else:
        return "unknown"   

if __name__ == '__main__':
    ## Retrieve input
    ## This is done here in case we need to return
    input = csv.reader(sys.stdin, lineterminator='\n')
    
    header = []
    first = True
  
    for inputResult in input:
        ## Process the first result as the header
        ## Also as an indication to initialize output handlers
        if first:
            ## Create header
            header = inputResult
            
            ## Initialize output handlers
            csv.writer(sys.stdout, lineterminator='\n').writerow(header)
            
            output = csv.DictWriter(sys.stdout, header, lineterminator='\n')

            first = False 
        
        else:
            outputResult = {}
            
            for x in range(0, len(inputResult)):
                outputResult[header[x]] = inputResult[x]
                
            if outputResult.has_key('priorities') and len(outputResult['priorities']) > 0:
                forwardLookup = True
                
                priority = 0
                
                priorityStrings = outputResult['priorities'].strip().split('|')
                
                for priorityString in priorityStrings:
                    priorityInt = Priority2Int(priorityString)
                    
                    if priorityInt > priority:
                        priority = priorityInt
                        
                priority = Int2Priority(priority)
                
                if outputResult.has_key('priority'):
                    outputResult['priority'] = priority
                    
                output.writerow(outputResult)
                
            else:
                sys.stdout.write('-1')