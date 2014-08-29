#!/bin/bash

################################################################
# TODOs:
#   1. Add input checks
#   2. Create boot-start scripts for each platform
#   3. Feed pug
#   4. More options for multiple input streams (label, segregate logs, etc)
#   5. Add sflow support
#   6. Add tags for inputs based on source parameters set by user
#   7. use dynamic subdirectories to store events from specific listeners
#   8. !! Convert to modular input and utilize Splunk-bundled Python to do this stuff !!
################################################################

printf "\nTA-FlowFIX v0.8\n"
printf "\nPlease send comments or suggestions to beaker@splunk.com/n"

printf "\nThis script will configure TA-FlowFIX on this system."

printf "\nRun this in the root of TA-flowfix on the system (as a user"
printf "\nwith \"owner\"/write privileges) that will listen for Netflow"
printf "\nor IPFIX streams. You will need either a full Splunk"
printf "\ninstallation or the Splunk Forwarder present.\n"

printf "\n\nThere are two modes of installation. One is for a"
printf "\nsystem running this Netflow/IPFIX receiver and using"
printf "\na Splunk Forwarder to send events to a Splunk Indexer.\n"

printf "\nThe other is for a stand alone Splunk instance, where"
printf "\nonly the eventtype transforms and tagging definitions"
printf "\nare added. A separate index will be created.\n"

printf "\nWhich type of installation will you be performing:\n"
printf "\n   (1) Netflow or IPFIX receiver/listener"
printf "\n   (2) \"netflow\" eventtype parser only\n"
printf "\nSelection: "
read installType

if [ $installType = 1 ]; then
    printf "\n\n1 selected... let's do this.\n"
elif [ $installType = 2 ]; then
    TA_PATH=`pwd`
    # name the index
    printf "\n\nName of Splunk index to use [ Default: netflow ]: "
    read splunkIndex
    if [[ -z "$splunkIndex" ]]; then
        splunkIndex="netflow"
    fi
    # write out indexes.conf
    printf "["$splunkIndex"]\n" > "$TA_PATH"/default/indexes.conf
    printf "homePath   = \$SPLUNK_DB/"$splunkIndex"/db\n" >> "$TA_PATH"/default/indexes.conf
    printf "coldPath   = \$SPLUNK_DB/"$splunkIndex"/colddb\n" >> "$TA_PATH"/default/indexes.conf
    printf "thawedPath = \$SPLUNK_DB/"$splunkIndex"/thaweddb\n" >> "$TA_PATH"/default/indexes.conf
    printf "\nThat was easy. Restart Splunk to enable this TA.\n\n"
    exit 1
else
    printf "\Selection not understood. Please start over.\n"
    exit 1
fi

printf "\nSystems currently supported for Netflow/IPFIX listening are:\n"
printf "\n   (*) Linux (64 bit)"
printf "\n   (*) Linux (32 bit)"
printf "\n   (*) FreeBSD (64 bit)"
#printf "\n   (*) FreeBSD (32 bit)"
#printf "\n   ( ) AIX 5.3 - 7.1 (POWER)"
#printf "\n   ( ) HP-UX 11.x (Itanium)\n"

# warning
printf "\n\nIf you already have a flowfix.sh in bin and inputs.conf/indexes.conf in"
printf "\ndefault, this WILL OVERWRITE them.\n\n"
read -r -p "CONTINUE [Y/n]: " keepGoing
if [[ $keepGoing =~ ^([yY][eE][sS]|[yY])$ || -z "$keepGoing" ]]; then
   printf "\nContinuing...\n\n"
else
   exit 1
fi

# check platform
OS=`uname -s` # currently supported: Linux and FreeBSD

CPU_TYPE=`uname -p` # currently supported: i686 and x86_64

if [ $CPU_TYPE = "i386" ] || [ $CPU_TYPE = "i686" ]; then
   CPU_TYPE="i686"
   CPU_ARCH="generic"
fi
if [[ `grep GenuineIntel /proc/cpuinfo` ]] && [ $CPU_TYPE = "x86_64" ]; then
   CPU_ARCH="core2"
fi
if [[ `grep AuthenticAMD /proc/cpuinfo` ]] && [ $CPU_TYPE = "x86_64" ]; then
   CPU_ARCH="opteron"
fi
if [[ `grep AuthenticAMD /proc/cpuinfo` ]] && [[ `grep sse4a /proc/cpuinfo` ]]; then
   CPU_ARCH="barcelona"
fi

KERN_OS_VER=`uname -r` # for later use

# set path for splunk instance
TA_PATH=`pwd`

printf "\nFull path location for this TA [ "$TA_PATH" ]: "
read customTA_PATH
   if [ "$customTA_PATH" != "" ]; then
      TA_PATH="$customTA_PATH"
   fi
printf "#!/bin/bash\n" > "$TA_PATH"/bin/flowfix.sh

# how long to keep the binary flows
printf "\n# of days to keep binary flow logs [ Default: 3 ]: "
read keepDays
   if [[ -z "$keepDays" ]]; then
      keepDays="3"
   fi

# name the index
printf "\nName of Splunk index to use [ Default: netflow ]: "
read splunkIndex
   if [[ -z "$splunkIndex" ]]; then
      splunkIndex="netflow"
   fi

# setup single or multiple listeners
printf "\nHow many listeners would you like to install on this system? [1]: "
read numListeners
   if [[ -z "$numListeners" ]]; then
      numListeners=1
   fi

for (( n=1; n<="$numListeners"; n++ ))
do
   printf "\nListener #"$n"\n"
   printf "\nNetflow [v5], [v9] or [IPFIX] [ Default: v5 ]: "
   read flowType
   if [[ -z "$flowType" ]]; then
        flowType="v5"
   fi
   
   printf "Specify IPv4 or IPv6 address to bind to listener [ Default: all ]: "
   read bindIP
    if [[ -z "$bindIP" ]] || [ $bindIP = "all" ]; then
        bindIP=""
    else
        bindIP="-b $bindIP"    
    fi
   
   # NOTE: fix so user cannot select the same port for multiple listeners at config time
   printf "UDP port to listen on: "
   read portNum
      if [[ `netstat -anl | grep "$portNum" | grep udp` ]]; then
         printf "\nPort is already actively listening!\n\n"
		 echo `netstat -anl | grep "$portNum" | grep udp`
		 printf "\nPlease check your system and start over.\n\n"
         exit 1
      fi
	  
   printf "# of seconds to rollover flow capture files for indexing [ Default: 120 ]: "
   read rollSeconds
      if [[ -z "$rollSeconds" ]]; then
        rollSeconds="120"
      fi
	  		 
   #printf "Start server with [splunkd] or at system [boot] [ Default: boot ]: "
   #read startMethod
   # NOTE: This only supports starting listeners with splunkd. v0.9 will introduce the option to start at system boot

   # write out of nfcapd configuration to TA-flowfix/bin/flowfix.sh
   printf "\n# Listener command for nfcapd $n - $flowType - $bindIP - $portNum" >> "$TA_PATH"/bin/flowfix.sh
   printf "\nif [ ! -f "$TA_PATH"/bin/nfcapd-"$n"-"$flowType"-"$bindIP"-"$portNum".pid ]; then\n" >> "$TA_PATH"/bin/flowfix.sh
   printf ""$TA_PATH"/bin/"$OS"_"$CPU_TYPE"_"$CPU_ARCH"/nfcapd -p "$portNum" "$bindIP" -T all -t "$rollSeconds" -l "$TA_PATH"/nfdump-binary -P "$TA_PATH"/bin/nfcapd-"$n"-"$flowType"-"$bindIP"-"$portNum".pid -D\n" >> "$TA_PATH"/bin/flowfix.sh
   printf "fi\n" >> "$TA_PATH"/bin/flowfix.sh
done

# write out nfdump -> CSV/ASCII procedures to TA-flowfix/bin/flowfix.sh
printf "\n# This part converts the binary flows to csv/ascii\n" >> "$TA_PATH"/bin/flowfix.sh
printf "if [[ \`find "$TA_PATH"/nfdump-binary | grep nfcapd.2\` ]]; then\n\n" >> "$TA_PATH"/bin/flowfix.sh
printf "FILES=\`ls "$TA_PATH"/nfdump-binary/nfcapd.2*\`\n\n" >> "$TA_PATH"/bin/flowfix.sh
printf "for FILE in \${FILES[*]}\ndo\n" >> "$TA_PATH"/bin/flowfix.sh
printf ""$TA_PATH"/bin/"$OS"_"$CPU_TYPE"_"$CPU_ARCH"/nfdump -qr \"\$FILE\" -o csv >> "$TA_PATH"/nfdump-ascii/nfdump-csv_\`date +\"%%Y%%m%%d%%H%%M%%S\"\`.log && rm \"\$FILE\"" >> "$TA_PATH"/bin/flowfix.sh
printf "\ndone;" >> "$TA_PATH"/bin/flowfix.sh
printf "\nfi" >> "$TA_PATH"/bin/flowfix.sh

# write out cleanup script
printf "\n\n# Cleanup files older than $keepDays" >> "$TA_PATH"/bin/flowfix.sh
printf "\nfind "$TA_PATH"/nfdump-binary -type f -mtime +"$keepDays" -exec rm -f {} \\;" >> "$TA_PATH"/bin/flowfix.sh 

# write out TA-flowfix/default/inputs.conf
printf "[monitor://"$TA_PATH"/nfdump-ascii]\n" > "$TA_PATH"/default/inputs.conf
printf "index = $splunkIndex\n" >> "$TA_PATH"/default/inputs.conf
printf "sourcetype = netflow\n"  >> "$TA_PATH"/default/inputs.conf
printf "disabled = false\n"  >> "$TA_PATH"/default/inputs.conf

printf "\n[script://"$TA_PATH"/bin/flowfix.sh]\n" >> "$TA_PATH"/default/inputs.conf
printf "index = $splunkIndex\n" >> "$TA_PATH"/default/inputs.conf
printf "interval = 60\n"  >> "$TA_PATH"/default/inputs.conf
printf "sourcetype = netflow\n"  >> "$TA_PATH"/default/inputs.conf
printf "disabled = false"  >> "$TA_PATH"/default/inputs.conf

# write out indexes.conf
printf "["$splunkIndex"]\n" >> "$TA_PATH"/default/indexes.conf
printf "homePath   = \$SPLUNK_DB/"$splunkIndex"/db\n" >> "$TA_PATH"/default/indexes.conf
printf "coldPath   = \$SPLUNK_DB/"$splunkIndex"/colddb\n" >> "$TA_PATH"/default/indexes.conf
printf "thawedPath = \$SPLUNK_DB/"$splunkIndex"/thaweddb\n" >> "$TA_PATH"/default/indexes.conf

# finishing touches
chmod -R 755 $TA_PATH

printf "\n\nSetup is complete! You will need to restart Splunk to enable changes.\n\n"
