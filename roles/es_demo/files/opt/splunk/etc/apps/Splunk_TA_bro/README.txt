BRO IDS Technology Add-on
----------------------------------------
	Author: Cedric LE ROUX / Splunk
	Version/Date: May 2014
	Source type(s): bro_conn, bro_ftp, bro_http, bro_ssl, bro_ssh, bro_dns, bro_dpd, bro_weird, ...
	Input requirements: Dynamic sourcetyping based on Bro log file names (conn.log => 'bro_conn') if sourcetype is set to 'bro'
	Has index-time operations: true
	Supported product(s): Bro IDS 2.1, 2.2 (dynamic field names extraction based on log files headers)

Using this Technology Add-on:
----------------------------------------
	Configuration: Manual
	Ports for automatic configuration: None
	Scripted input setup: Not applicable

Additional Configuration Information:
----------------------------------------
  Please refer to the Splunk_TA_bro/SPEC/inputs.conf.spec for configuration of inputs and outputs for the Bro environment.

  Sample inputs.conf to monitor logs files:

    [monitor:///var/opt/bro/logs/current/...]
    disabled = 0
    followTail = 0
    sourcetype = bro
    index = bro
    crcSalt = <SOURCE>
    whitelist = \.log$

  Sample inputs.conf to monitor pcap files:
    [pcap_monitor://MyRepo]
    bro_bin = /opt/bro/bin/bro
    bro_merge = 0
    bro_opts = -C
    bro_script = None
    bro_seeds = None
    content_maxsize = 1024
    index = bro
    path = /var/pcap
    recursive = 0
    run_maxtime = 1800
    store_dir = /var/log/bro/

  Adjust those settings to fit your environment.


Copyright (C) 2009-2014 Splunk Inc. All Rights Reserved.
