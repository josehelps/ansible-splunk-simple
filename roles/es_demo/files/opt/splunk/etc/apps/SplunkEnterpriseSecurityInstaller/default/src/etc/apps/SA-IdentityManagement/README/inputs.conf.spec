[identity_manager://default]
* Configures an input for defining a lookup table as a source of asset
* or identity information.

category = <string>
* [Required] Category of the lookup. User-defined, for ad-hoc use. Not used in
* the merged asset list.

description = <string>
* [Optional] A description of the asset or identity lookup.

master_host = <string>
* [DEFAULT_STANZA_ONLY] Defines the master host if search head pooling is enabled.
* Only the master host will perform threat list downloads. If SHP is enabled this
* MUST be non-empty AND match the name of a server in the pool.

target = <string>
* The target for the input stanza. Must be one of "asset" or "identity".

url = <string>
* The source of the asset or identity information. Acceptable values are:
* 
*    lookup://<lookup_name>
*        where <lookup_name> corresponds to the name of the stanza in 
*        transforms.conf that defines the lookup table and is unique across all
*        apps 
*
* The merge process will incorporate all source files into the consolidated asset
* or identity table.