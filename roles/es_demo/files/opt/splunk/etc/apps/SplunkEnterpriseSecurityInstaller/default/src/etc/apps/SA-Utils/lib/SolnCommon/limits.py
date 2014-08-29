'''
Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
'''
import sys
import splunk

from .error import ConfErrors
from models import SplunkLookupLimits


def get_limits(stanza_name, key):
    '''Retrieve a specific limits.conf stanza.
    
    @param stanza_name: The stanza name to retrieve.
    @param key: A Splunk session key.
    @return: The stanza as a Splunk<Stanza>Limits object, or None.
    '''
    
    mapper = {'lookup': SplunkLookupLimits}
    
    stanza_model = mapper.get(stanza_name, None)
    if stanza_model:
        try:
            return stanza_model.all(sessionKey=key)[0]
        except splunk.ResourceNotFound as e:
            sys.stderr.write(ConfErrors.ERR_NO_LIMIT_STANZA + ': %s\n' % str(e))
            pass
        except Exception as e:
            sys.stderr.write(ConfErrors.ERR_UNKNOWN_EXCEPTION + ': %s\n' % str(e))
            pass
    else:
        sys.stderr.write(ConfErrors.ERR_MODEL_UNDEFINED + ': %s\n' % str(e))
        
    return None
