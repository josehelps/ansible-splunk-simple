'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))
from SolnCommon.lookup_conversion.merge import CsvFileMergeHandler


class IdentityManagerMergeHandler(CsvFileMergeHandler):
    
    def __init__(self, *args, **kwargs):
        super(IdentityManagerMergeHandler, self).__init__(*args, **kwargs)
