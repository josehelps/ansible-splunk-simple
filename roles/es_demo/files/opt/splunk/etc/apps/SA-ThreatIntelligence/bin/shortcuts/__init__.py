import csv
import gzip
import logging
import logging.handlers
import math
import os
import random
import re
import StringIO
import struct
import time
import collections

import splunk.util as util

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


class Invocation:
    @staticmethod
    def getInvocationID():
        nowTime = util.mktimegm(time.gmtime())
        
        salt = random.randint(0, 100000)
        
        invocation_id = str(nowTime) + ':' + str(salt)
        
        return invocation_id
        

class Message:
    """
    Represents messages that need to be displayed in the user interface.
    """
    SEVERITY_INFO = 'info'
    SEVERITY_WARN = 'warn'
    SEVERITY_ERROR = 'error'
    SEVERITY_FATAL = 'fatal'
    
    def __init__(self, message, severity):
        self.severity = severity
        self.message = message
        
    def __str__(self):
        return self.message


class Page:
    """
    Represents a page in the paginator.
    """
    
    def __init__(self, page_number, offset, is_current_page=False, is_prev=False, is_next=False):
        self.page_number = page_number
        self.is_current_page = is_current_page
        self.is_prev = is_prev
        self.is_next = is_next
        self.offset = offset
        
    def __str__(self):
        return str(self.page_number)


class Paginator:
    """
    Provides a mechanism for computed pagination 
    """
    
    def __init__(self, total_entries, offset, entries_per_page, add_prev_next=True):    
        self.total_entries = total_entries
        self.offset = offset
        self.entries_per_page = entries_per_page
        
        self.end_offset_current_page = self.__end_offset_current_page__()
        self.__populate_pages__(add_prev_next)
        
    def get_page_contents(self, items):
        """
        Get the items for the given page from the given array
        """
        
        return items[self.offset : self.offset + self.entries_per_page ]
    
    def __populate_pages__(self, add_prev_next=True):
        """
        Populate an internal data structure that will contain the pages to be displayed.
        """
        self.pages = []
        
        # Calculate the previous offset
        if self.has_previous():
            prev_offset = self.offset - self.entries_per_page
        else:
            prev_offset = 0
        
        # Calculate the next offset
        if self.has_next():
            next_offset = self.offset + self.entries_per_page
        else:
            next_offset = self.last_offset()
        
        # Add the previous button
        if add_prev_next and self.has_previous():
            self.pages.append( Page( "Previous", prev_offset, False, is_prev=True) )
        
        # Add the pages
        for page_num in range(0, self.pages_count() ):
            
            page_offset = page_num * self.entries_per_page
            
            if page_offset == self.offset:
                self.pages.append( Page(page_num + 1, page_offset, True) )
            else:
                self.pages.append( Page(page_num + 1, page_offset, False) )
                
        # Add the next button
        if add_prev_next and self.has_next():
            self.pages.append( Page( "Next", next_offset, False, is_next=True) )
        
    def __end_offset_current_page__(self):
        """
        Provides the end offset in the current page
        """
        
        last_in_offset = self.offset + (self.entries_per_page - 1)
        
        if last_in_offset > (self.total_entries - 1):
            return self.total_entries - 1
        else:
            return last_in_offset
        
    def last_offset(self):
        """
        Get the offset value of the last number
        """
        
        return (self.pages_count() - 1) * self.entries_per_page
        
    def pages_count(self):
        """
        Get the number of pages  (not including the previous and next links)
        """
        
        pages_num = (self.total_entries * 1.0) / self.entries_per_page
        
        pages_num = math.ceil(pages_num)
        
        return int(pages_num)
    
    def has_previous(self):
        """
        Determine if a previous page exists.
        """
        
        if self.offset > 0:
            return True
        else:
            return False
    
    def has_next(self):
        """
        Determine if a next page exists
        """
        
        if (self.offset + self.entries_per_page) >= self.total_entries:
            return False
        else:
            return True
    
    def previous_offset(self):
        """
        Get the offset value for the previous page. Returns the current if alread at the current page.
        """
        
        prev_offset = self.offset - self.entries_per_page
        
        if prev_offset < 0:
            return 0
        else:
            return prev_offset
    
    def __iter__(self):
        return self.pages.__iter__()
    
    def __getitem__(self, key):
        return self.pages[key]
    
    def __len__(self):
        return self.pages.__len__()


class NoSessionKeyException(Exception):
    """
    To be thrown if we could not get a session key
    """
    pass


class GzipHandler:
    '''Class for handling gzip-formatted string content.'''
    # TODO: come up with better name than GzipHandler

    # Error messages
    # TODO: ensure that these are read-only
    ERR_INVALID_FORMAT  = 'File is not gzip format.'
    ERR_SIZE_MISMATCH   = 'Gzip file size does not match actual.'

    def __init__(self):
        pass

    @classmethod
    def checkFormat(self, data):
        '''Take a string and validate whether it is in gzip
           format. 
        '''
        # Check for gzip header.
        # Bytes 0 and 1 should be (per RFC 1952):
        # ID1 = 31 (0x1f, \037), ID2 = 139 (0x8b, \213)
        return data[0:2] == '\037\213'

    @classmethod
    def decompress(self, data):
       '''Decompress a string containing gzip-compressed data,
          performing basic validation. Returns the decompressed
          data or raises ValueError with an error string.
       '''

       # 1 - Check format.
       if not self.checkFormat(data):
           raise ValueError(self.ERR_INVALID_FORMAT)

       # 2 -- Read length of file from last four bytes of data.
       # This should be the size of the uncompressed data mod 2^32
       # Note that unpack() always returns a tuple even for one item
       sizeInt, = struct.unpack('i', data[-4:])
    
       # 3 -- Decompress the string
       decompressor = gzip.GzipFile(fileobj=StringIO.StringIO(data), mode='rb')
       text = decompressor.read()
    
       # 4 -- Check decompressed size.
       if len(text) != sizeInt:
           raise ValueError(self.ERR_SIZE_MISMATCH)

       return text
   
   
class Duration:
    
    DURATION_MAP = [
                ("y", 31556926),
                ("yr", 31556926),
                ("yrs", 31556926),
                ("year", 31556926),
                ("years", 31556926),
                ("mon", 2629744),
                ("M", 2629744),
                ("month", 2629744),
                ("months", 2629744),
                ("q", 3 * 2629744),
                ("qtr", 3 * 2629744),
                ("qtrs", 3 * 2629744),
                ("quarter", 3 * 2629744),
                ("quarters", 3 * 2629744),
                ("d", 86400),
                ("day", 86400),
                ("days", 86400),
                ("w", 7 * 86400),
                ("week", 7 * 86400),
                ("weeks", 7 * 86400),
                ("h", 3600),
                ("hr", 3600),
                ("hrs", 3600),
                ("hour", 3600),
                ("hours", 3600),
                ("m", 60),
                ("min", 60),
                ("minute", 60),
                ("minutes", 60),
                ("s", 1),
                ("sec", 1),
                ("secs", 1),
                ("second", 1),
                ("seconds", 1)
                ]


    @staticmethod
    def duration_from_readable(duration):
        """
        Takes a duration as a string (like "1d") and produces the duration in seconds.
        """
    
        # If the duration is an empty string, then the user is not using throttling
        if duration is None or ( isinstance(duration, basestring) and len(duration.strip()) == 0):
            return None
    
        # Create a regular expression that is capable of matching the duration
        regex = re.compile("\s*(?P<duration>[0-9]+)\s*(?P<units>([a-z]+))?",re.IGNORECASE)
        
        # Try to perform a match
        m = regex.match(str(duration))
    
        # If we did not get a match, then raise an exception
        if m is None:
            raise ValueError("Invalid duration specified (%s)." % (str(duration)) ) 
    
        # If we did get a match then extract the components
        units = m.groupdict()['units']
        duration = int(m.groupdict()['duration'])
    
        # Per-digest/per-event alerting cannot use zero or negative integers as the suppression window.
        if duration <= 0:
            raise ValueError("Duration cannot be negative or zero.") 

        # If units are None, then treat the duration as seconds
        if units is None:
            return duration
        
        # Get the multiplier from the duration map
        for duration_entry in Duration.DURATION_MAP:
        
            # If the units match the given entry, then return the value in seconds
            if duration_entry[0] == units:
                return duration_entry[1] * duration
         
        # We should never get here since the regex should have caught any 
        # units that do not correspond to a duration.
        raise ValueError("Invalid duration specified (%s)." % ( str(duration)) )


    @staticmethod
    def duration_to_readable(duration_seconds):
        """
        Takes a duration (in seconds) and produces a friendly string version (like "1d" for 1 day)
        """
    
        # If the duration is none, then return an empty string
        if duration_seconds is None:
            return ""
    
        # Iterate through the duration map and find
        for duration_entry in Duration.DURATION_MAP:
        
            # Get the number of seconds that a given duration unit corresponds to
            seconds = duration_entry[1]
        
            # Get a string that represents the duration
            if duration_seconds >= seconds and (duration_seconds % seconds) == 0:
                return str(duration_seconds / seconds) + duration_entry[0]
    
        # If no match could be found, then consider the duration in units of seconds
        return str(duration_seconds) + "s"


class NotableOwner:

    NOTABLE_OWNERS = []
        
    @classmethod
    def getOwners(cls, force_reload=False):

        # Return cached value unless this is the first such call,
        # or if force_reload is specified.
        if len(cls.NOTABLE_OWNERS) == 0 or force_reload:
            headerElement = 'owner'

            # Find the owners table within Splunk
            csvFile = make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "lookups", "notable_owners.csv"])
            # Read CSV file into the list, skipping the header line.
            with open(csvFile, 'rU') as f:
                
                d = {}
                
                for row in csv.reader(f):
                    if row[0] != headerElement:
                        
                        # Use the username if the realname is blank
                        if row[1] == '':
                            d[ row[0] ] = row[0]
                        else:
                            d[ row[0] ] = row[1]
                
                # Sort the dictionary
                def getkey(owner):
                    if owner[0] == 'unassigned':
                        return 'zzzzz'
                    elif owner[1] == '':
                        return owner[0]
                    else:
                        return owner[1]
                
                od = collections.OrderedDict(sorted(d.items(), key=lambda x: getkey(x)))
                
                # Store the owner dictionary
                cls.NOTABLE_OWNERS = od
        
        return cls.NOTABLE_OWNERS

class Status:

    STATUSES = []
        
    @classmethod
    def getStatuses(cls, force_reload=False):

        # Return cached value unless this is the first such call,
        # or if force_reload is specified.
        if len(cls.STATUSES) == 0 or force_reload:
            headerElement = 'status'

            # Find the status table within Splunk
            csvFile = make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "lookups", "reviewstatuses.csv"])
            # Read CSV file into the list, skipping the header line.
            with open(csvFile, 'rU') as f:
                
                d = {}
                
                for row in csv.reader(f):
                    if row[0] != headerElement:
                        d[ row[0] ] = row[1]
                
                cls.STATUSES = d
                
        return cls.STATUSES

class Severity:

    SEVERITIES = []
        
    @classmethod
    def getSeverities(cls, force_reload=False):

        # Return cached value unless this is the first such call,
        # or if force_reload is specified.
        if len(cls.SEVERITIES) == 0 or force_reload:
            headerElement = 'severity'

            # Find the urgency table within Splunk
            csvFile = make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "lookups", "urgency.csv"])
            # Read CSV file into the list, skipping the header line.
            with open(csvFile, 'rU') as f: 
                cls.SEVERITIES = set([row[0].lower() for row in csv.reader(f) if row[0] != headerElement])
                
        return cls.SEVERITIES

    @classmethod
    def from_readable_severity(cls, severity):
        """
        Takes the readable severity and returns the version that is saved in correlation searches.conf
        """
        if isinstance(severity, basestring):
            if severity.strip().lower() in cls.getSeverities():
                return severity.strip().lower()
        return 'unknown'
    
class Urgency:

    URGENCIES = []
        
    @classmethod
    def getUrgencies(cls, force_reload=False):

        # Return cached value unless this is the first such call,
        # or if force_reload is specified.
        if len(cls.URGENCIES) == 0 or force_reload:
            headerElement = 'urgency'

            # Find the urgency table within Splunk
            csvFile = make_splunkhome_path(["etc", "apps", "SA-ThreatIntelligence", "lookups", "urgency.csv"])
            # Read CSV file into the list, skipping the header line.
            with open(csvFile, 'rU') as f: 
                cls.URGENCIES = set([row[2].lower() for row in csv.reader(f) if row[2] != headerElement])
                
        return cls.URGENCIES

    @classmethod
    def from_readable_urgency(cls, urgency):
        """
        Takes the readable urgency and returns the version that is saved in correlation searches.conf
        """
        if isinstance(urgency, basestring):
            if urgency.strip().lower() in cls.getUrgencies():
                return urgency.strip().lower()
        return 'unknown'
    
class Logger:
    
    @classmethod
    def setup_logger(name, level=logging.WARNING, maxBytes=25000000, backupCount=5 ):

        logfile = make_splunkhome_path(["var", "log", "splunk", name+'.log'])
        
        logger = logging.getLogger(name)
        logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
        logger.setLevel(level)

        file_handler = logging.handlers.RotatingFileHandler(logfile, maxBytes, backupCount)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
   
        return logger
