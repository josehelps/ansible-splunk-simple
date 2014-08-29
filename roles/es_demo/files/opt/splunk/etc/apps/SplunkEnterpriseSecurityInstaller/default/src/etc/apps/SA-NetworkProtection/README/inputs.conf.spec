[whois://default]
* Configures an input for obtaining WHOIS network information. Currently we
* provide support for the following external data retrieval methods:
*
*	1. domaintools.com [external API]
*   2. system "whois" command
*
* Accuracy of data returned by the modular input will be greatly increased by 
* the use of an external API, due to the extremely unpredictable nature of 
* WHOIS data. External API access requires the creation of a user account.

api_host = <value>
* [API only, optional] An API host, if required by the provider.

api_user = <value>
* [API only, optional] A user account to use for API access, if required by the provider.

app = <value>
* [API only, optional] Splunk application context used to retrieve stored 
* credentials. This should usually be "SA-NetworkProtection" but can refer to
* any app that the user has placed API credentials in.

owner = <value>
* [API only, optional] A Splunk user that has access to any stored credentials
* in use. Currently, this should always be "admin".

provider = <value>
* [Required] The data provider. Must correspond to the name of the Python class that implements
* the provider.

proxy_port = <value>
* [API only, optional] A proxy server port.

proxy_server = <value>
* [API only, optional] A proxy server name.

proxy_user = <value>
* [API only, optional] A proxy server user name. If present, must correspond to a 
* credential name in Splunk's secure credential store.

queue_interval = <value>
* [Required] The interval (in seconds) between attempts to process the queue.

query_interval = <value>
* [Required] The interval (in seconds) between successive queries.

reverse_dns_enabled = <true|false>
* Attempt to resolve IP address to domain names. Disabled by default.
* WARNING: Enabling reverse DNS resolution may expose the existence of your
* system to an attacker.
