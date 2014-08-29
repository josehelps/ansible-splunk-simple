'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import os
import sys
import splunk.Intersplunk

try:

	results = ''
	results = splunk.Intersplunk.readResults(None, None, True)

except Exception, e:
    results = splunk.Intersplunk.generateErrorResults(str(e))

splunk.Intersplunk.outputResults(results)
