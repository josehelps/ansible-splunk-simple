import csv
import os
import sys
import time

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "bin"]))
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-Utils", "lib"]))

import network.whois_handlers as handlers
from SolnCommon import netutils
from SolnCommon.modinput import logger
from SolnCommon.modinput import ModularInput
from SolnCommon.modinput.fields import BooleanField
from SolnCommon.modinput.fields import Field
from SolnCommon.modinput.fields import IntegerField
from SolnCommon.modinput.fields import RangeField
from SolnCommon.modinput.fields import FieldValidationException

#import logging
#logger.setLevel(logging.DEBUG)

class NetworkModularInput(ModularInput):

    def __init__(self):
                
        scheme_args = {'title': "Network Queries",
                       'description': "Perform network queries.",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}

        args = [
                Field("api_host", "API host", "Hostname used to access external API, if applicable.", required_on_create=True, required_on_edit=True),
                Field("api_user", "API user", "User name used to access external API, if applicable.", required_on_create=True, required_on_edit=True),
                Field("app", "Splunk application context", "Splunk application context used to retrieve stored credentials.", required_on_create=False, required_on_edit=False),
                Field("owner", "Splunk owner", "Splunk user account used to retrieve stored credentials.", required_on_create=False, required_on_edit=False),
                Field("provider", "Provider", "The name of the provider for this input.", required_on_create=True, required_on_edit=True),
                RangeField("proxy_port", "Proxy port", "The proxy server port (only applicable to methods that use HTTP).", low=0, high=65535, required_on_create=False, required_on_edit=False),
                Field("proxy_server", "Proxy server", "The proxy server (only applicable to methods that use HTTP).", required_on_create=False, required_on_edit=False),
                Field("proxy_user", "Proxy user", "The proxy user name (only applicable to methods that use HTTP).", required_on_create=False, required_on_edit=False),
                IntegerField("query_interval", "Query interval", "Interval between queries, in seconds.", required_on_create=True, required_on_edit=True),
                IntegerField("queue_interval", "Queue interval", "Interval between attempts to process the queue, in seconds.", required_on_create=True, required_on_edit=True),
                BooleanField("reverse_dns_enabled", "Reverse DNS enabled", "Attempt to resolve IP addresses to hostnames prior to making WHOIS queries.", required_on_create=False, required_on_edit=False),
                ]
        
        ModularInput.__init__(self, scheme_args, args)

    def do_validation(self, in_stream=sys.stdin):
        # TODO: 2-stage validation:
        # 1. Validate field contents.
        # 2. Add validation of params via the chosen provider here.
        
        data = self.get_validation_data(in_stream)
        
        try:
            self.validate(data)
            return True
        except FieldValidationException as e:
            self.print_error(str(e))
            return False
    
    def get_handler(self, name):
        return getattr(handlers, name)
              
    def run(self, stanzas):

        logger.debug("Entering run method.")
        logger.debug("Input config: {0}".format(str(self._input_config)))
        logger.debug("Cleaned params: {0}".format(str(stanzas)))

        # If an alternative session key for testing was provided 
        # via command-line arguments, use it.
        try:
            if self._alt_session_key:
                self._input_config.session_key = self._alt_session_key
        except (AttributeError, NameError):
            # No alternate session key defined.
            pass
        
        # Get the first stanza (which should be the only stanza); otherwise exit.
        if stanzas:
            stanza = stanzas[0]
        else:
            logger.info('No WHOIS inputs configured. Exiting.')
            sys.exit(0)

        # Get the handler for the current configuration.
        try:
            handler = getattr(handlers, stanza['provider'])
        except AttributeError as e:
            logger.error("Query handler not found: %s" % (str(e)))
            raise e

        # Prepare the handler
        query_handler = handler(logger, self._input_config.session_key, **stanza)
        
        # Prepare the results for XML streaming output.
        doc = self._create_document()

        # Begin endless loop.
        while True:
            # Get the list of queries. This is a list of files, each in CSV format:
            #     _time,domain
            filenames = os.listdir(self._input_config.checkpoint_dir)
            
            # Check for checkpointed files; if none exist, sleep for queue_interval
            # seconds.
            if len(filenames) > 0:
    
                # Accept only "csv" checkpoint files.
                for filename in [f for f in filenames if f.endswith('.csv')]:
                    try:
                        checkpointed_file = open(os.path.join(self._input_config.checkpoint_dir, filename), 'r')
                    except IOError:
                        logger.error('Error opening checkpoint file: {0}'.format(checkpointed_file.name))
                        continue

                    logger.info('Processing checkpoint file: {0}'.format(checkpointed_file.name))
                    queries = csv.DictReader(checkpointed_file)
                        
                    for query in queries:

                        qstr = query['domain']
                        if stanza.get('reverse_dns_enabled', False):
                            # Attempt DNS resolution in case this is an IP address.
                            resolved_query = netutils.resolve(qstr)
                            if resolved_query:
                                qstr = resolved_query
                        else:
                            # IP addresses in incoming data will not be resolved.
                            pass

                        # Run the query
                        result = query_handler.run(qstr)

                        # Format the result to include the domain and resolved domain, if found.
                        # Result can be None at this point; format will return a properly-
                        # formatted JSON error message if so.
                        data = query_handler.format(query['domain'], qstr, result)

                        if data:
                
                            # The "data" field should be populated from the query.
                            # The "host" field is implicit for this type of modular input.
                            event_dict = {'stanza': stanza,
                                          'time': query['_time'],
                                          'data': data,
                                          'index': stanza['index'],
                                          'source': stanza['source'],
                                          'sourcetype': stanza['sourcetype']}
                        
                            event = self._create_event(doc,
                                params=event_dict,
                                stanza=stanza,
                                unbroken=stanza.get('unbroken', False),
                                close=False)
                
                            # If using unbroken events, the last event must have been
                            # added with a "</done>" tag.
                            output = self._print_event(doc, event)
                
                            # Print the XML stream to stdout.
                            sys.stdout.write(output)
                            sys.stdout.flush()
                                            
                            # Sleep for a number of seconds between queries.
                            time.sleep(stanza['query_interval'])
                        
                        else:
                            # This should never happen since the handler's format()
                            # method should always return data.
                            logger.error('ERROR: WHOIS query handler failed on domain %s', query['domain'])
                    
                    # Close resources and remove the checkpoint file.
                    checkpointed_file.close()
                    try:
                        # This may fail on Windows if file is still in use.
                        os.remove(checkpointed_file.name)
                        logger.info('Removed checkpoint file %s', checkpointed_file.name)
                    except IOError as e:
                        logger.error('ERROR: Failed to remove checkpoint file %s', checkpointed_file.name)
    
            else:
                logger.info('No checkpoint files found for WHOIS lookup... sleeping for %s seconds', stanza['queue_interval'])
                # Wait for new checkpoint files to be created.
                time.sleep(stanza['queue_interval'])
                
        # end while loop

if __name__ == '__main__':
    logger.info("Executing modular input.")
    modinput = NetworkModularInput()
    try:
        # execute() Loops indefinitely
        modinput.execute()
    except Exception as e:
        sys.exit(1)
    sys.exit(0)
