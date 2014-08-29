'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import logging
import logging.handlers
import lxml.etree as et
import os
import random
import splunk.Intersplunk
import splunk.rest as rest
import splunk.util as util
import sys

from time import gmtime, strftime
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
def setup_logger():
	"""
	Setup a logger for the search command
	"""
	
	logger = logging.getLogger('expectedactivity')
	logger.setLevel(logging.DEBUG)
	
	file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'expectedactivity.log']), maxBytes=25000000, backupCount=5)
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	file_handler.setFormatter(formatter)
	
	logger.addHandler(file_handler)
	
	return logger

logger = setup_logger()

			  
## Parses time strings using /search/timeparser endpoint
def timeParser(ts='now', sessionKey=None):
	getargs = {}
	getargs['time'] = ts
	
	tsStatus, tsResp = rest.simpleRequest('/search/timeparser', sessionKey=sessionKey, getargs=getargs)
		
	root = et.fromstring(tsResp)  
	
	ts = root.find('dict/key')
	
	if ts is not None:
		ts = util.parseISO(ts.text, strict=True)
	
	else:
		logger.warn("Could not retrieve timestamp for specifier '%s' from /search/timeparser" % (ts) )

	return ts


if __name__ == '__main__':
	## Create a unique identifier for this invocation
	nowTime = util.mktimegm(gmtime())
	salt = random.randint(0, 100000)
	invocation_id = str(nowTime) + ':' + str(salt)
    
	## Log initialization
	logger.info('invocation_id=%s; signature=Starting expectedactivity' % (invocation_id))
	
	fields = None
	interval = None
	earliest = None
	latest = None
	append = True
	
	## Override Defaults w/ opts below
	if len(sys.argv) > 1:
		for a in sys.argv:
			if a.startswith('fields='):
				where = a.find('=')
				fields = a[where+1:len(a)]
			elif a.startswith('interval='):
				where = a.find('=')
				interval = a[where+1:len(a)]
			elif a.startswith('earliest='):
				where = a.find('=')
				earliest = a[where+1:len(a)]
			elif a.startswith('latest='):
				where = a.find('=')
				latest = a[where+1:len(a)]
			elif a.startswith('append='):
				where = a.find('=')
				append = a[where+1:len(a)]
				
				if util.normalizeBoolean(append) == True:
					append = True
				else:
					append = False
	
	## Split fields
	if fields is not None:
		fields = fields.split(',')
		
	else:
		fields = []

	## Check fields
	if len(fields) <= 0:
		signature = 'Fields list cannot be empty'
		logger.error('invocation_id=%s; signature=%s' % (invocation_id, signature))
		results = splunk.Intersplunk.generateErrorResults('Error; %s' % signature)
		splunk.Intersplunk.outputResults(results)
		sys.exit()
	
	logger.info('invocation_id=%s; signature=Fields retrieved; fields=%s' % (invocation_id, str(fields)))
	
	## Convert interval
	try:
		interval = int(interval)
		
	except:
		interval = None
		
	## Check interval
	if interval is None or interval < 0:
		signature = 'Interval parameter must be a valid integer greater than zero'
		logger.error('invocation_id=%s; signature=%s; interval=%s' % (invocation_id, signature, interval))
		results = splunk.Intersplunk.generateErrorResults('Error; %s' % signature)
		splunk.Intersplunk.outputResults(results)
		sys.exit()
		
	logger.info('invocation_id=%s; signature=Interval retrieved; interval=%s' % (invocation_id, interval))
	
	## Retrieve results and settings
	results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
	
	## Get session key
	sessionKey = settings.get('sessionKey', None)
	
	## Check earliest
	try:
		earliestTime = timeParser(earliest, sessionKey)
		
	except:
		earliestTime = None
		
	if earliestTime is None:
		signature = 'Earliest parameter was invalid or could not be processed'
		logger.error('invocation_id=%s; signature=%s; earliest=%s' % (invocation_id, signature, earliest))
		results = splunk.Intersplunk.generateErrorResults('Error; %s' % signature)
		splunk.Intersplunk.outputResults(results)
		sys.exit()
		
	else:
		earliestEpoch = util.dt2epoch(earliestTime)
		earliestEpoch = int(earliestEpoch)
		
	logger.info('invocation_id=%s; signature=Earliest retrieved; earliest=%s' % (invocation_id, earliest))

	## Check latest
	try:
		latestTime = timeParser(latest, sessionKey)
	
	except:
		latestTime = None
	
	if latestTime is None:
		signature = 'Latest parameter was invalid or could not be processed'
		logger.error('invocation_id=%s; signature=%s; earliest=%s' % (invocation_id, signature, latest))
		results = splunk.Intersplunk.generateErrorResults('Error; %s' % signature)
		splunk.Intersplunk.outputResults(results)
		sys.exit()
		
	else:
		latestEpoch = util.dt2epoch(latestTime)
		latestEpoch = int(latestEpoch)
		
	logger.info('invocation_id=%s; signature=Latest retrieved; latest=%s' % (invocation_id, latest))
	
	###### Determine unique combinations of provided fields ######
	## Initialize expected activity array
	expectedActivity = []
	
	## Verify > 0 results
	if len(results) > 0:
		requiredFields = fields[:]
		
		## Test first item to verify all required fields are present
		for key in results[0]:
			## Remove the field from the list of required fields
			try:
				requiredFields.remove(key)
			
			except ValueError:
				pass # Field not available, probably because it is not required
		
		## Test length of required fields
		if len(requiredFields) > 0:
			e = 'All required fields (%s) must be available in the result set' % (','.join(fields))
			logger.critical(e)
			results = splunk.Intersplunk.generateErrorResults('Error; %s' % e)
			splunk.Intersplunk.outputResults(results)
			sys.exit()
		
		else:
			## Iterate each result
			for x in range(0,len(results)):
				activity = {}
				
				## Iterate each key, val in result
				for key, val in results[x].items():
					## If key in fields
					if key in fields:
						activity[key] = val
				
				## If key-val combinations not in expectedActivity		
				if activity not in expectedActivity:
					expectedActivity.append(activity)
		
		## Zero out results if append=False
		if not append:
			results = []
		
		## Test the length of expected activity
		if len(expectedActivity) > 0:
			
			logger.info('invocation_id=%s; signature=Expected activity deduced; items=%s' % (invocation_id, len(expectedActivity)))
			
			#logger.debug(expectedActivity)
			
			while earliestEpoch <= latestEpoch:
				for activity in expectedActivity:
					outputResult = {}
					outputResult['_time'] = earliestEpoch
					
					for key, val in activity.items():
						outputResult[key] = val
						
					results.append(outputResult)
				
				earliestEpoch += interval
						
		else:
			logger.error('invocation_id=%s; signature=Expected activity set empty' % (invocation_id))
			
	else:
		logger.warn('invocation_id=%s; signature=Result set empty' % (invocation_id))
	
	## output
	splunk.Intersplunk.outputResults(results)
	logger.info('invocation_id=%s; signature=Finishing expectedactivity' % (invocation_id))