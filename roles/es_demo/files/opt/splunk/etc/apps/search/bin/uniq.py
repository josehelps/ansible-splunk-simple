#   Version 4.0
import sys,splunk.Intersplunk

results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

newresults = []
oldresult = None
for result in results:
    if result != oldresult:
        newresults.append(result)
        oldresult = result
        
splunk.Intersplunk.outputResults(newresults)

