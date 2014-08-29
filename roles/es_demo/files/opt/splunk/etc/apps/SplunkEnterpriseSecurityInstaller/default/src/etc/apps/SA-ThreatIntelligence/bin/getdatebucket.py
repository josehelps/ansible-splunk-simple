'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''

from math import *
import time
from datetime import datetime, timedelta

def getDateBucket(event_date, frequency_secs, round_to_next_bucket=True):
    """Returns an integer representing which time bucket the given time represents
    >>> getDateBucket( datetime(2010,7,8), 30*86400)
    493
    """
    t_stamp = 1.0*time.mktime(event_date.timetuple())
    
    # This calculates the current bucket
    bucket_float = t_stamp / frequency_secs
    bucket = int(round(floor(bucket_float),1))

    if round_to_next_bucket == False:
        return bucket

    # If the current time is at least halfway through the current bucket, then return the next bucket
    if (bucket_float-bucket) > 0.5:
        return bucket+1
    else:
        return bucket
