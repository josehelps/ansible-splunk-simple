import argparse
import logging
import logging.handlers
import os
import re
import splunk.Intersplunk
import sys

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.models.field import Field, IntField, BoolField
from splunk.models.base import SplunkAppObjModel


## Setup the logger
def setup_logger():
    """
    Setup a logger for the search command
    """
   
    logger = logging.getLogger('datamodelinfo')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
   
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'datamodelinfo.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
   
    logger.addHandler(file_handler)
   
    return logger

logger = setup_logger()


class DataModels(SplunkAppObjModel):
    resource = 'data/models'
    
    name         = Field()
    acl          = Field(api_name='eai:acl')
    acceleration = BoolField()
    retention    = Field(api_name='acceleration.earliest_time')
    cron         = Field(api_name='acceleration.cron_schedule')
    

class DataModelSummarization(SplunkAppObjModel):
    resource = 'admin/summarization'
  
    name          = Field()
    access_count  = IntField(api_name='summary.access_count')
    access_time   = Field(api_name='summary.access_time')
    buckets       = IntField(api_name='summary.buckets')
    buckets_size  = IntField(api_name='summary.buckets_size')
    complete      = Field(api_name='summary.complete')
    digest        = Field(api_name="eai:digest")
    earliest      = Field(api_name='summary.earliest_time')
    is_inprogress = Field(api_name='summary.is_inprogress')
    last_error    = Field(api_name='summary.last_error')
    last_sid      = Field(api_name='summary.last_sid')
    latest        = Field(api_name='summary.latest_time')
    mod_time      = Field(api_name='summary.mod_time')
    retention     = IntField(api_name='summary.time_range')  
    size          = IntField(api_name='summary.size')
    summary_id    = Field(api_name='summary.id')


def get_options(argv):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('datamodel', nargs='*')
    return parser.parse_args(argv)


if __name__ == '__main__':
    
    logger.info('Starting datamodelinfo search command')

    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    results = []  # we don't care about incoming results
  
    sessionKey = settings.get('sessionKey', None)
    
    if sessionKey is not None:

        datamodels = ''
        try:
            options = get_options(sys.argv[1:])
            datamodels = ' AND ({})'.format(' OR '.join(['name=' + dm for dm in options.datamodel if re.match('^[A-Za-z0-9_]+$', dm)]))
        except argparse.ArgumentError:
            # Default to showing all data models
            pass
            
        # Get the data models
        logger.info('Retrieving accelerated data model listing')
        data_models = DataModels.search('acceleration=1{}'.format(datamodels), count_per_req=100, sessionKey=sessionKey)
        
        logger.info('Successfully retrieved %s models' % (len(data_models)))
                      
        ## Iterate the models
        logger.info('Iterating through retrieved models')
        for data_model in data_models:
            data_model_name            = data_model.name
            
            logger.info('Processing data model: %s' % (data_model_name))         

            data_model_app             = data_model.acl.get('app')

            summary_id                 = '/services/' + DataModelSummarization.resource + '/tstats:DM_' + data_model_app + '_' + data_model_name

            try:
                data_model_summarization = DataModelSummarization.get(id=summary_id, sessionKey=sessionKey)
                
                result                   = {}
                result['datamodel']      = data_model_name
                result['app']            = data_model_app
                result['cron']           = data_model.cron
                result['access_count']   = data_model_summarization.access_count
                result['access_time']    = data_model_summarization.access_time
                result['buckets']        = data_model_summarization.buckets
                result['buckets_size']   = data_model_summarization.buckets_size
                result['complete']       = data_model_summarization.complete
                result['digest']         = data_model_summarization.digest
                result['earliest']       = data_model_summarization.earliest
                result['is_inprogress']  = data_model_summarization.is_inprogress
                result['last_error']     = data_model_summarization.last_error
                result['last_sid']       = data_model_summarization.last_sid
                result['latest']         = data_model_summarization.latest
                result['mod_time']       = data_model_summarization.mod_time   
                result['retention']      = data_model_summarization.retention
                result['size']           = data_model_summarization.size
                result['summary_id']     = data_model_summarization.summary_id
                
                results.append(result)    

            except:
                logger.warn('Could not get summarization info for model: %s' % (summary_id))
            
    else:
        logger.critical('Unable to retrieve data models: Session Key unavailable')

    splunk.Intersplunk.outputResults(results)
    logger.info('Finishing datamodelinfo search command')
