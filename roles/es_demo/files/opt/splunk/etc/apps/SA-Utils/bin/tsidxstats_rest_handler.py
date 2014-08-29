'''
Copyright (C) 2005 - 2011 Splunk Inc. All Rights Reserved.
'''
import logging
import logging.handlers
import os
import splunk.admin as admin
import subprocess
import re

import splunk.clilib.cli_common
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.models.field import Field
from splunk.models.base import SplunkAppObjModel


## Setup the logger
def setup_logger():
   """
   Setup a logger for the REST handler.
   """
   
   logger = logging.getLogger('tsidxstats_rest_handler')
   logger.setLevel(logging.DEBUG)
   
   file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'tsidxstats_rest_handler.log']), maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
   
   return logger

logger = setup_logger()

## Determine $SPLUNK_DB path
def get_envvar_path(envvar):
    envvar_clean = envvar.lstrip('$')
    
    try:
        envvar_val = os.environ[envvar_clean]
        
    except KeyError:
        raise admin.ArgValidationException("%s could not be found in os environment variables" % envvar)
    
    return os.path.normpath(envvar_val)


class Index(SplunkAppObjModel):
    resource = 'data/indexes'
    
    tsidx_home = Field(api_name="tsidxStatsHomePath")


class TsidxStatsRH(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  ## admin.py constants
  REQUESTED_ACTIONS = { '1': 'ACTION_CREATE', '2': 'ACTION_LIST', '4': 'ACTION_EDIT', '8': 'ACTION_REMOVE', '16': 'ACTION_MEMBERS', '32': 'ACTION_RELOAD' }
  
  ## Permissions
  READ_CAPABILITY   = 'list_tsidxstats'
  
  ## Globals
  TSIDXPROBE_BINARY = os.path.join(make_splunkhome_path(['bin']), 'tsidxprobe')
  TSIDXSTATS_DIR    = os.path.join(splunk.clilib.cli_common.splunk_db, 'tsidxstats')
  
  logger.info('TSIDXPROBE_BINARY Global: %s' % TSIDXPROBE_BINARY)
  logger.info('TSIDXSTATS_DIR Global: %s' % TSIDXSTATS_DIR)
  
  def setup(self):
      logger.info('Setting up tsidxstats_rest_handler')
      
      ## set read capability
      # self.setReadCapability(TsidxStatsRH.READ_CAPABILITY)
        
  @staticmethod
  def get_namespace_and_filename( name ):
        a = re.split(r"([\\]|[/])", name)
        
        tsidx_namespace = a[0]
        file_name       = a[2]
        
        return tsidx_namespace, file_name
 
  def handleList(self, confInfo):      
      """
      Handles listing of a correlation search
      """
      ## Get requested action
      actionStr = str(self.requestedAction)
      if TsidxStatsRH.REQUESTED_ACTIONS.has_key(actionStr):
          actionStr = TsidxStatsRH.REQUESTED_ACTIONS[actionStr]
          
      logger.info('Entering %s' % (actionStr))
      
      ## Refresh
      #self.handleReload()
      
      ## Get the tsidxStatsHomePath specified in indexes.conf ($SPLUNK_DB/tsidxStats if not specified)
      logger.info('Retrieving TSIDX home path specified by indexes.conf')
      
      ## The following would be faster, but assumes someone didn't doing something weird with the 'main' index
      ## I am going to stick with ".all()" for the sake of resiliency
      #index_info = Index.get(id=Index.build_id(name="main", namespace=None, owner=None))
      index_info = Index.all(sessionKey=self.getSessionKey())[0]
      
      TSIDX_HOME = index_info.tsidx_home
      logger.info('TSIDX_HOME per indexes.conf: %s' % TSIDX_HOME)
      
      ## Validate the tsidxStatsHomePath as specified by indexes.conf
      ## if index_info is None or empty set 
      if TSIDX_HOME is None or len(TSIDX_HOME) < 1:
          ## use default
          logger.info('Using Global TSIDXSTATS_DIR')
          TSIDXSTATS_DIR = TsidxStatsRH.TSIDXSTATS_DIR
      
      ## if index_info has a path; let's validate it    
      else:
          logger.info('Using TSIDX_HOME to build TSIDXSTATS_DIR')
          
          TSIDX_HOME = TSIDX_HOME.split(os.sep)
          
          for x in xrange(0,len(TSIDX_HOME)):
              if TSIDX_HOME[x] == '$SPLUNK_HOME':
                  TSIDX_HOME[x] = make_splunkhome_path([''])
                  
              elif TSIDX_HOME[x] == '$SPLUNK_DB':
                  TSIDX_HOME[x] = splunk.clilib.cli_common.splunk_db

              elif TSIDX_HOME[x].startswith('$'):
                  TSIDX_HOME[x] = get_envvar_path(TSIDX_HOME[x])
                  
          TSIDXSTATS_DIR = os.sep.join(TSIDX_HOME)
              
          logger.info('TSIDXSTATS_DIR: %s' % TSIDXSTATS_DIR)

      ## Get the list of tsidx files from TSIDXSTATS_DIR
      logger.info('Getting TSIDX files list')
      
      ## initialize stats object
      tsidxstats = []
      
      ## iterate TSIDXSTATS_DIR
      for dirname, dirnames, filenames in os.walk(TSIDXSTATS_DIR):
          for filename in filenames:
              if filename.endswith('.tsidx'):
                  ## get the tsidx collection (last item in split)
                  collection = os.path.split(dirname)[-1]
                  
                  ## join the collection and tsidx filename
                  collection = os.path.join(collection, filename)
              
                  ## add collection to the list
                  tsidxstats.append(collection)
      
      ## iterate discovered tsidxstats collection files
      logger.info('Probing TSIDX files')
      
      for collection in tsidxstats:
          collection_path = os.path.join(TSIDXSTATS_DIR, collection)
          
          ## create a collection stanza
          confInfo[collection].append('disabled', '0')
          
          try:
              ## run tsidxprobe
              collection_probe = subprocess.Popen([TsidxStatsRH.TSIDXPROBE_BINARY, '-m', collection_path], stdout=subprocess.PIPE)
              
              ## get the data
              collection_probe = collection_probe.communicate()[0]
              
              ## split the data by line
              collection_probe = collection_probe.split('\n')
              
              ## iterate over each line in the output
              for metric in collection_probe:
                  ## split key = value pairs
                  metric = metric.split('=')
                  
                  ## if we have a valid key = value pair
                  if len(metric) == 2:
                      confInfo[collection].append(str(metric[0].strip()), str(metric[1].strip()))
                      
              ## Add several other useful parameters
              confInfo[collection]["tsidxStatsHomePath"] = TSIDXSTATS_DIR # We are including this because Splunk doesn't include this in indexes.conf unless specifically overridden
              confInfo[collection]["file_path"]          = collection_path # The full path to the TSIDX file
              
              tsidx_namespace, filename = TsidxStatsRH.get_namespace_and_filename(collection)
              confInfo[collection]["tsidx_namespace"]    = tsidx_namespace
              confInfo[collection]["file_name"]          = filename
              
              try:
                  confInfo[collection]["file_size_on_disk"] = os.stat(collection_path).st_size
              except OSError:
                  # File could not be found.
                  # This is likely be because the file was renamed (which Splunk does).
                  pass

          except Exception as e:
              logging.exception(e)
      
      logger.info('%s completed successfully' % (actionStr) ) 
              
  def handleReload(self, confInfo=None):
      """
      Handles refresh/reload of the configuration options
      """
      pass
  
  def handleRemove(self, confInfo):
      pass   
                               
# initialize the handler
admin.init(TsidxStatsRH, admin.CONTEXT_APP_AND_USER)