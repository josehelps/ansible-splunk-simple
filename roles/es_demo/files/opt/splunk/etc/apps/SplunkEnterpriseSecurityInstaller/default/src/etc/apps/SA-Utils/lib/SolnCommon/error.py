import abc


class Errors(object):
    '''Abstract base class for error classes.
    
    Subclasses of this class do nothing but store error messages.

    A class is used instead of a dict because:
       1. Python 2.7.x lacks a consensus enum implementation.
       2. Using class attributes enables features such as tab completion
          in IPython and most IDEs, as well as permitting static detection
          of references to nonexistent error messages. Conversely dictionary
          accesses cannot be checked statically, which leads to ValueErrors
          at runtime.
    '''
    __metaclass__ = abc.ABCMeta

    # These errors are generic to all subclasses.
    ERR_UNKNOWN_ERROR = "An unknown error occurred."
    ERR_UNKNOWN_EXCEPTION = "An unknown exception occurred."
    
    @classmethod
    def formatErr(cls, err, msg=None):
        '''Standard error message format.
        
        @param err: The error message.
        @param msg: An optional message to append to the output.
        '''

        if msg:
            return '%s: %s\n' % (err or cls.ERR_UNKNOWN_ERROR, msg)
        else:
            return '%s\n' % (err or cls.ERR_UNKNOWN_ERROR)

    @classmethod
    def formatErrWithTb(cls, err, tb, msg=None):
        '''Standard error message format including an exception traceback.
        
        @param err: The error message.
        @param tb: The exception traceback.
        @param msg: An optional message to append to the output.
        '''
        
        # TODO: Complete this.
        pass


# Error classes shared across apps.
class CliErrors(Errors):
    '''Command-line errors.'''

    ERR_NO_AUTH_INFO = "All authentication methods failed."
    ERR_NO_CLI_AUTH_INFO = "Authentication failed (command line usage requires a valid username and password)."
    ERR_NO_PASSAUTH_INFO = "Authentication failed (passAuth may not be enabled in inputs.conf)."


class ConfErrors(Errors):
    '''Class for errors related to conf files.'''
    ERR_MODEL_UNDEFINED = "The requested limits.conf stanza could not be retrieved because no model was defined"
    ERR_NO_LIMIT_STANZA = "The requested limits.conf stanza could not be found"


class LookupConversionErrors(Errors):
    '''Class which does nothing but store error messages.

       Using a class instead of a dict because:
       1. Python 2.7.x lacks a consensus enum implementation.
       2. Using class attributes in most IDEs enables tab completion, as well as
          alerting when we reference a nonexistent error message. Conversely
          dictionary accesses can not be checked statically, which leads to
          ValueErrors at runtime.
    '''

    ERR_AMBIGUOUS_INPUT_RECORD = "An input record could not be converted without ambiguity and was discarded" 
    ERR_BAD_INPUT_DATA = "Some lines in the input CSV contained bad data"
    ERR_BAD_INPUT_FIELD_COUNT = "Some lines in the input CSV contained an invalid number of columns"
    ERR_BAD_LOOKUP_SPEC = "Invalid lookup name specified for conversion"
    ERR_DEFERRED_CONVERSION_NOT_IMPLEMENTED = "Deferred conversion was requested but not implemented for a field"
    ERR_EXTRA_INPUT_FIELDS = "Some extra fields were present in the input CSV"
    ERR_INVALID_INPUT_FIELD = "Invalid input field data"
    ERR_INVALID_INPUT_FORMAT = "One or more column names in the input CSV were invalid"
    ERR_INVALID_INPUT_RECORD = "An input line contained invalid input and was discarded"
    ERR_INVALID_IP_OR_CIDR = "Invalid IP address or CIDR block was specified"
    ERR_INVALID_IP_RANGE = "Invalid IP range was specified"
    ERR_INVALID_MAC = "Invalid MAC address was specified"
    ERR_INVALID_MAC_RANGE = "Invalid MAC range was specified"
    ERR_LOOKUP_READ_FAILED = "Lookup table could not be read"
    ERR_LOOKUP_TOO_LARGE = "A WILDCARD or CIDR lookup table was generated larger than max_memtable_bytes in size"
    ERR_LOOKUP_NOT_DEFINED_FOR_KEY = "A key field was defined without a corresponding output lookup table"
    ERR_MISSING_INPUTFIELD = "An expected field was missing from the input"
    ERR_LOOKUP_CREATION_FAILED = "A lookup table could not be created"
    ERR_MISSING_INPUT_FIELDS = "Some fields were missing from the input CSV"
    ERR_MISSING_LOOKUP = "The source lookup table does not exist"
    ERR_NO_AUTH_INFO = "Authentication failed (command line usage requires a username or username and password)"
    ERR_NO_LOOKUP = "Lookup table was not found"
    ERR_NO_PASSAUTH = "Authentication failed (passAuth may not be enabled in inputs.conf)"
    ERR_POSTPROCESSING_NOT_IMPLEMENTED = "Postprocessing routine must be defined by a subclass of FieldMapping"
    ERR_PREMATURE_SCRIPT_EXIT = "Script exited prematurely due to invalid data in the input CSV"
    ERR_RANGES_NOT_FOUND = "IP ranges not found for asset id"
    ERR_TEMPORARY_FILE_NOT_CREATED = "Temporary output file was not created"
    ERR_TEMPORARY_FILE_REMOVAL_FAILED = "A temporary file could not be removed."
    ERR_UNKNOWN_ERROR = "An unknown error occurred"
    ERR_UNKNOWN_EXCEPTION = "Unknown exception"
    ERR_UNDEFINED_HANDLER = "No handler defined for expanding the requested type of input lookup table"


class ModInputErrors(Errors):
    '''Modular input errors.'''
    
    ERR_MODINPUT_STATUS_FAILED = "A modular input exited abnormally"
