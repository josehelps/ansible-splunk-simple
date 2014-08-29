'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import os
import re
import splunk.Intersplunk
import sys
import subprocess
import time
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Defaults
addonResults = []
results = ''
host = False
nslookup = False

theTime = time.mktime(time.localtime())

## Method for testing for insecure input
def TestInput(host):
	validRex = re.compile('^([A-Za-z0-9\.\:\_\-]+)$')
	validMatch = validRex.match(host)
	
	if validMatch:
		if host == validMatch.group(1):
			return host
		
		else:
			return False
	
	else:
		return False
	
if __name__ == '__main__':
	## Override Defaults w/ opts below
	if len(sys.argv) > 1:
		for a in sys.argv:
			if a.startswith('host='):
				where = a.find('=')
				host = a[where+1:len(a)]
				
			elif a.startswith('dest='):
				where = a.find('=')
				host = a[where+1:len(a)]
				
	if host:
		host = TestInput(host)
		if not host:
			results = splunk.Intersplunk.generateErrorResults('Error; Invalid characters detected in host input')
		
		else:	
			## Retrive results and settings
			results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
			results = []
		
			nslookupFile = make_splunkhome_path(['var', 'spool', 'splunk', str(int(theTime)) + '-' + host.replace('.', '-') + '.nslookup'])
		
			try:
				nslookup = subprocess.Popen(['nslookup', host], stdout=subprocess.PIPE)
						
			except:
				pass
		
			if nslookup:
				nslookup = nslookup.communicate()[0]
			
				addonResult = { '_time' : theTime, '_raw' : nslookup, 'dest' : host }
				addonResults.append(addonResult)
		
				results = addonResults
				
				nslookupFH = open(nslookupFile, 'w')
				nslookupFH.write(nslookup)
				nslookupFH.close()
	
	else:
		results = splunk.Intersplunk.generateErrorResults('Error; Host not specified')
		
	splunk.Intersplunk.outputResults(results)