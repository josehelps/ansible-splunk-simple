[threatlist://default]
* Configures an input for downloading a threat list or other source of threat
* intelligence from a remote site. Currently we provide support for the
* following protocols:
*
*    1. HTTP [basic and digest authentication]
*    2. HTTPS [basic and digest authentication]
*    3. Local lookup table
*    

delim_regex = <string>
* [Conditionally Required] A regular expression used to delimit the threat list. One of
* extract_regex OR delim_regex is required. 

description = <string>
* [Optional] A description of the threat list.

extract_regex = <string>
* [Optional] A regular expression matching groups that will be extracted from
* the threat list. One of extract_regex OR delim_regex is required. 

fields = <string>
* [Required] A list of fields to be extracted from the threat list by the parser.
* Multiple fields may be specified as field.0,field.1. This list MUST be comma-
* separated.

ignore_regex = <string>
* [Conditionally Required] A regular expression matching lines that will be 
* ignored in the threat list.

initial_delay = <seconds>
* [DEFAULT_STANZA_ONLY, Optional] An initial delay in seconds imposed before the
* modular input begins downloading any files. This is used to alleviate startup 
* load.

master_host = <string>
* [DEFAULT_STANZA_ONLY] Defines the master host if search head pooling is enabled.
* Only the master host will perform threat list downloads. If SHP is enabled this
* MUST be non-empty AND match the name of a server in the pool.

post_args = <string>
* A list of POST arguments to be sent with the request. Applicable to HTTP(S)
* URLs only. Argument should be specified in one of the following formats:
*
*    key=value
*    key="value"
*
* An additional special syntax is provided for purposes of retrieving Splunk
* stored credentials:
*
*    key=$user:<username>$
*
* Example:
*
*    key=$user:norse$
*
* If this form is used, the password corresponding to the stored credential
* will be retrieved and used as a POST argument. This is convenient in cases
* where an API key must be sent as a POST argument to complete the HTTP(S) 
* request, but true HTTP authentication is not required.

proxy_port = <integer>
* [API only, optional] A proxy server port.

proxy_server = <string>
* [API only, optional] A proxy server name.

proxy_user = <string>
* [API only, optional] A proxy server user name. If present, must correspond to a
* credential name in the secure credential store.

retries = <integer>
* [Optional] The number of times to attempt a specific download before marking
* the download as failed.

retry_interval = <seconds>
* [Required] The interval (in seconds) between retries.

skip_header_lines = <integer>
* [Optional] The number of header lines to skip when reading the threatlist. 
* For any stanzas that use "lookup://<lookup_name>" to specify a Splunk lookup
* table as a threatlist, this should be set to 1 to avoid reading processing the
* CSV header as a valid threatlist entry. Failure to set this will not impede 
* processing but may result in verbose errors in the python_modular_input.log
* file.

site_user = <string>
* [Optional] The user used for authentication to the remote site. This is
* distinct from proxy credentials. If present, must correspond to a credential
* name in the secure credential store.

target = <string>
* [DEFAULT STANZA ONLY] Target lookup table for the merge process.

type = <string>
* [Required] Type of the threat list. Arbitrary. Can be overloaded depending
* on customer needs (e.g., "Threatlist:Malware"). This does not override the
* "category" field which may be present in a threatlist's contents, but is 
* intended to be used as a simple categorization mechanism for threatlists.

timeout = <seconds>
* [DEFAULT_STANZA_ONLY, Optional] The interval (in seconds) before a download 
* attempt times out. Defaults to 30 seconds if not specified.

url = <url>
* [Required] The remote URL to download. Must begin with one of the following:
* "http://", "https://", "lookup://". If "lookup://" is used, instead of
* downloading a remote file, the local lookup table referred to will be incorporated
* into the merged threatlist. In this case, download, interval, and proxy parameters
* are ignored.

weight = <integer>
* [Required] The weight assigned to the threatlist, between 1 and 100. A higher
* weight will result in higher risk score for being assigned to IPs that appear
* in Splunk events corresponding to values in the threatlist.

[threatlist_manager://default]
* Configures a modular input that merges information from all defined
* "threatlist" input stanzas.

master_host = <string>
* [DEFAULT_STANZA_ONLY] Defines the master host if search head pooling is enabled.
* Only the master host will perform threat list downloads. If SHP is enabled this
* MUST be non-empty AND match the name of a server in the pool.
