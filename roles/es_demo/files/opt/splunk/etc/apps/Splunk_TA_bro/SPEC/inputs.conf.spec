[pcap_monitor://default]
* Configure an input for watching pcap files in a directory.

path = <string>
* A path where the pcap files are stored.

recursive = <bool>
* Monitor recursively the input directory set by path.

store_dir = <string>
* A path where the output logs of Bro will be stored. 

bro_bin = <string>
* A path where the Bro binary is located.

bro_opts   = <string> 
* Bro options to use when processing a pcap file

bro_script = <string> 
* Bro script to use when processing a pcap file

bro_seeds  = <bool>
* A seed file to use to predict/fix Bro UID.

bro_merge  = <bool>
* Indicate wether if the packet content should be merged in logs

content_maxsize = <integer>
* Maximum allowed content size when merging it in logs (in bytes, 0 to set to 'no limit')

run_maxtime = <integer>
* Maximum time allowed per Bro instance per pcap file (in seconds, 0 to disable)

