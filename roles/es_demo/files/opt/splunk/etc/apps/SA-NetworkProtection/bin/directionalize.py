'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import csv
import os
import re
import sys
import splunk
import splunk.Intersplunk
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

app = 'SA-NetworkProtection'
file = 'directionalize.csv'

## Override Defaults w/ opts below
if len(sys.argv) > 1:
	for a in sys.argv:
		if a.startswith('app='):
			where = a.find('=')
			app = a[where+1:len(a)]
		elif a.startswith('file='):
			where = a.find('=')
			file = a[where+1:len(a)]
		
dest_ports = []
exceptions = {}

first = True
srcFields = []
destFields = []
results = ''
	
## Retrive results and settings
results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

## Determine path to lookup
baseStorage = make_splunkhome_path(["etc", "apps", app, 'lookups', file])

try:
	dest_ports = csv.reader(open(baseStorage, 'rU'))

except:
	results = splunk.Intersplunk.generateErrorResults('Error; directionalize exceptions file: ' + baseStorage + ' not found')
	
for dest_port in dest_ports:
	exceptions[dest_port[0]] = "yes"

for x in range(0,len(results)):
	tempFields = {}
	
	if first:
		for k,v in results[x].items():
			if k.startswith('dest'):
				destFields.append(k)

			elif k.startswith('src'):
				srcFields.append(k)		
		
		if results[x].has_key('src_port') and results[x].has_key('dest_port') and not exceptions.has_key(results[x]['dest_port']):
			if int(results[x]['src_port']) < int(results[x]['dest_port']):
				for destField in destFields:
					if results[x].has_key(destField):
						if len(results[x][destField]) > 0:
							tempFields[destField.replace('dest', '!!foo!!')] = results[x][destField]
						del results[x][destField]
					
				for srcField in srcFields:
					if results[x].has_key(srcField):
						if len(results[x][srcField]) > 0:
							results[x][srcField.replace('src', 'dest')] = results[x][srcField]
						del results[x][srcField]
					
				for k,v in tempFields.items():
					results[x][k.replace('!!foo!!', 'src')] = v

		first = False
	
	else:
		if results[x].has_key('src_port') and results[x].has_key('dest_port') and not exceptions.has_key(results[x]['dest_port']):
			if int(results[x]['src_port']) < int(results[x]['dest_port']):
				for destField in destFields:
					if results[x].has_key(destField):
						if len(results[x][destField]) > 0:
							tempFields[destField.replace('dest', '!!foo!!')] = results[x][destField]
						del results[x][destField]
					
				for srcField in srcFields:
					if results[x].has_key(srcField):
						if len(results[x][srcField]) > 0:
							results[x][srcField.replace('src', 'dest')] = results[x][srcField]
						del results[x][srcField]
					
				for k,v in tempFields.items():
					results[x][k.replace('!!foo!!', 'src')] = v

splunk.Intersplunk.outputResults(results)
