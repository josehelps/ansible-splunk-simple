'''
Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
'''
import os, sys
import logging

#Setup logging for this test run
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-5s  %(message)s',
                    filename='ta-ossec-test.log',
                    filemode='w')

logger = logging.getLogger('ta-ossec-python-fw')
logger.info('Logging setup completed.')
logger.info("sys.path: " + str(sys.path))