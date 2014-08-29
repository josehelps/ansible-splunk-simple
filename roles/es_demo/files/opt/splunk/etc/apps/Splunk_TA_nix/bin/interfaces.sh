#!/bin/sh                                                                                                
# Copyright 2009-2012 Splunk, Inc.                                                                       
#                                                                                                        
#   Licensed under the Apache License, Version 2.0 (the "License");                                      
#   you may not use this file except in compliance with the License.                                     
#   You may obtain a copy of the License at                                                              
#                                                                                                        
#       http://www.apache.org/licenses/LICENSE-2.0                                                       
#                                                                                                        
#   Unless required by applicable law or agreed to in writing, software                                  
#   distributed under the License is distributed on an "AS IS" BASIS,                                    
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.                             
#   See the License for the specific language governing permissions and                                  
#   limitations under the License.      

. `dirname $0`/common.sh

HEADER='Name       MAC                inetAddr         inet6Addr                                  Collisions  RXbytes          TXbytes          Speed        Duplex'
FORMAT='{mac = length(mac) ? mac : "?"; collisions = length(collisions) ? collisions : "?"; RXbytes = length(RXbytes) ? RXbytes : "?"; TXbytes = length(TXbytes) ? TXbytes : "?"; speed = length(speed) ? speed : "?"; duplex = length(duplex) ? duplex : "?"}'
PRINTF='END {printf "%-10s %-17s  %-15s  %-42s %-10s  %-16s %-16s %-12s %-12s\n", name, mac, IPv4, IPv6, collisions, RXbytes, TXbytes, speed, duplex}'

if [ "x$KERNEL" = "xLinux" ] ; then
	assertHaveCommand ifconfig
	assertHaveCommand dmesg

	CMD_LIST_INTERFACES="eval ifconfig | tee $TEE_DEST | grep 'Link encap:Ethernet' | tee -a $TEE_DEST | cut -d' ' -f1 | tee -a $TEE_DEST"
	CMD='ifconfig'
	GET_MAC='{NR == 1 && mac = $5}'
	GET_IPv4='{if ($0 ~ /inet addr:/) {split($2, a, ":"); IPv4 = a[2]}}'
	GET_IPv6='{$0 ~ /inet6 addr:/ && IPv6 = $3}'
	GET_COLLISIONS='{if ($0 ~ /collisions:/) {split($1, a, ":"); collisions = a[2]}}'
	GET_RXbytes='{if ($0 ~ /RX bytes:/) {split($2, a, ":"); RXbytes= a[2]}}'
	GET_TXbytes='{if ($0 ~ /TX bytes:/) {split($6, a, ":"); TXbytes= a[2]}}'
	GET_ALL="$GET_MAC $GET_IPv4 $GET_IPv6 $GET_COLLISIONS $GET_RXbytes $GET_TXbytes"
	FILL_BLANKS='{length(speed) || speed = "<n/a>"; length(duplex) || duplex = "<n/a>"; length(IPv4) || IPv4 = "<n/a>"; length(IPv6) || IPv6= "<n/a>"}'
	BEGIN='BEGIN {RXbytes = TXbytes = collisions = 0}'

	echo "$HEADER"
	for iface in `$CMD_LIST_INTERFACES`
	do
		# ethtool(8) would be preferred, but requires root privs; so we use dmesg(8), whose [a] source can be cleared, and [b] output format varies (so we have less confidence in parsing)
		SPEED=`dmesg  | awk '/[Ll]ink( is | )[Uu]p/ && /'$iface'/ {for (i=1; i<=NF; ++i) {if (match($i, /([0-9]+)([Mm]bps)/))             {print $i} else { if (match($i, /[Mm]bps/))   {print $(i-1) "Mb/s"} } } }' | sed '$!d'`
		DUPLEX=`dmesg | awk '/[Ll]ink( is | )[Uu]p/ && /'$iface'/ {for (i=1; i<=NF; ++i) {if (match($i, /([\-\_a-zA-Z0-9]+)([Dd]uplex)/)) {print $i} else { if (match($i, /[Dd]uplex/)) {print $(i-1)       } } } }' | sed 's/[-_]//g; $!d'`
		$CMD $iface | tee -a $TEE_DEST | awk "$BEGIN $GET_ALL $FILL_BLANKS $PRINTF" name=$iface speed=$SPEED duplex=$DUPLEX
		echo "Cmd = [$CMD $iface];     | awk '$BEGIN $GET_ALL $FILL_BLANKS $PRINTF' name=$iface speed=$SPEED duplex=$DUPLEX" >> $TEE_DEST
	done
elif [ "x$KERNEL" = "xSunOS" ] ; then
	assertHaveCommandGivenPath /usr/sbin/ifconfig
	assertHaveCommand kstat

	CMD_LIST_INTERFACES="eval /usr/sbin/ifconfig -au | tee $TEE_DEST | egrep -v 'LOOPBACK|netmask' | tee -a $TEE_DEST | grep flags | cut -d':' -f1"
	if [ SOLARIS_8 = false ] && [ SOLARIS_9 = false] ; then
		GET_COLLISIONS_RXbytes_TXbytes_SPEED_DUPLEX='($1=="collisions") {collisions=$2} (/duplex/) {duplex=$2} ($1=="rbytes") {RXbytes=$2} ($1=="obytes") {TXbytes=$2} ($1=="ifspeed") {speed=$2; speed/=1000000; speed=speed "Mb/s"}' 
	else
		GET_COLLISIONS_RXbytes_TXbytes_SPEED_DUPLEX='($1=="collisions") {collisions=$2} ($1=="duplex") {duplex=$2} ($1=="rbytes") {RXbytes=$2} ($1=="obytes") {TXbytes=$2} ($1=="ifspeed") {speed=$2; speed/=1000000; speed=speed "Mb/s"}'
	fi
	GET_IP='/ netmask / {for (i=1; i<=NF; i++) {if ($i == "inet") IPv4 = $(i+1); if ($i == "inet6") IPv6 = $(i+1)}}'
    GET_MAC='{if ($1 == "ether") {split($2, submac, ":"); mac=sprintf("%02s:%02s:%02s:%02s:%02s:%02s", submac[1], submac[2], submac[3], submac[4], submac[5], submac[6])}}'
	FILL_BLANKS='{IPv4 = IPv4 ? IPv4 : "<n/a>"; IPv6 = IPv6 ? IPv6 : "<n/a>"}'
	GET_ALL="$GET_COLLISIONS_RXbytes_TXbytes_SPEED_DUPLEX $GET_IP $GET_MAC $FILL_BLANKS"

	echo "$HEADER"
	for iface in `$CMD_LIST_INTERFACES`
	do
		echo "Cmd = [$CMD_LIST_INTERFACES]" >> $TEE_DEST
		NODE=`uname -n`
		if [ SOLARIS_8 = false ] && [ SOLARIS_9 = false] ; then
			CMD_DESCRIBE_INTERFACE="eval kstat -c net -n $iface ; /usr/sbin/ifconfig $iface 2>/dev/null"
		else
			CMD_DESCRIBE_INTERFACE="eval kstat -n $iface ; /usr/sbin/ifconfig $iface 2>/dev/null"
		fi
		$CMD_DESCRIBE_INTERFACE | tee -a $TEE_DEST | $AWK "$GET_ALL $FORMAT $PRINTF" name=$iface node=$NODE
		echo "Cmd = [$CMD_DESCRIBE_INTERFACE];     | $AWK '$GET_ALL $FORMAT $PRINTF' name=$iface node=$NODE" >> $TEE_DEST
	done
elif [ "x$KERNEL" = "xAIX" ] ; then
	assertHaveCommandGivenPath /usr/sbin/ifconfig
	assertHaveCommandGivenPath /usr/bin/netstat

	CMD_LIST_INTERFACES="eval /usr/sbin/ifconfig -au | tee $TEE_DEST | egrep -v 'LOOPBACK|netmask|inet6|tcp_sendspace' | tee $TEE_DEST | grep flags | cut -d':' -f1"
	GET_COLLISIONS_RXbytes_TXbytes_SPEED_DUPLEX='($1=="Single"){collisions_s=$4} ($1=="Multiple"){collisions=collisions_s+$4} ($1=="Bytes:") {RXbytes=$4 ; TXbytes=$2} ($1=="Media" && $3=="Running:") {speed=$4"Mb/s" ; duplex=$6}'
	GET_IP='/ netmask / {for (i=1; i<=NF; i++) {if ($i == "inet") IPv4 = $(i+1); if ($i == "inet6") IPv6 = $(i+1)}}'
	GET_MAC='/^Hardware Address:/{mac=$3}'
	FILL_BLANKS='{IPv4 = IPv4 ? IPv4 : "<n/a>"; IPv6 = IPv6 ? IPv6 : "<n/a>"}'
	GET_ALL="$GET_COLLISIONS_RXbytes_TXbytes_SPEED_DUPLEX $GET_IP $GET_MAC $FILL_BLANKS"

	echo "$HEADER"
	for iface in `$CMD_LIST_INTERFACES`
	do
		echo "Cmd = [$CMD_LIST_INTERFACES]" >> $TEE_DEST
		NODE=`uname -n`
		CMD_DESCRIBE_INTERFACE="eval netstat -v $iface ; /usr/sbin/ifconfig $iface"
		$CMD_DESCRIBE_INTERFACE | tee -a $TEE_DEST | $AWK "$GET_ALL $FORMAT $PRINTF" name=$iface node=$NODE
		echo "Cmd = [$CMD_DESCRIBE_INTERFACE];     | $AWK '$GET_ALL $FORMAT $PRINTF' name=$iface node=$NODE" >> $TEE_DEST
	done
elif [ "x$KERNEL" = "xDarwin" ] ; then
	assertHaveCommand ifconfig
	assertHaveCommand netstat

	CMD_LIST_INTERFACES='ifconfig -u'
	CHOOSE_ACTIVE='/^[a-z0-9]+: / {sub(":", "", $1); iface=$1} /status: active/ {print iface}'

	GET_MAC='{$1 == "ether" && mac = $2}'
	GET_IPv4='{$1 == "inet" && IPv4 = $2}'
	GET_IPv6='{if ($1 == "inet6") {sub("%.*$", "", $2);IPv6 = $2}}'
	GET_SPEED_DUPLEX='{if ($1 == "media:") {gsub("[^0-9]", "", $3); speed=$3 "Mb/s"; sub("-duplex.*", "", $4); sub("<", "", $4); duplex=$4}}'
	GET_RXbytes_TXbytes_COLLISIONS='{if ($4 == mac) {RXbytes = $7; TXbytes = $10; collisions = $11}}'
	GET_ALL="$GET_MAC $GET_IPv4 $GET_IPv6 $GET_SPEED_DUPLEX $GET_RXbytes_TXbytes_COLLISIONS"

	echo "$HEADER"
	for iface in `$CMD_LIST_INTERFACES | tee $TEE_DEST | awk "$CHOOSE_ACTIVE"`
	do
		echo "Cmd = [$CMD_LIST_INTERFACES];  | awk '$CHOOSE_ACTIVE'" >> $TEE_DEST
		CMD_DESCRIBE_INTERFACE="eval ifconfig $iface ; netstat -b -I $iface"
		$CMD_DESCRIBE_INTERFACE | tee -a $TEE_DEST | awk "$GET_ALL $PRINTF" name=$iface 
		echo "Cmd = [$CMD_DESCRIBE_INTERFACE];     | awk '$GET_ALL $PRINTF' name=$iface" >> $TEE_DEST
	done
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    assertHaveCommand ifconfig
    assertHaveCommand lanadmin
    assertHaveCommand lanscan
    assertHaveCommand netstat

    CMD='lanscan'
    LANSCAN_AWK='/^Hardware/ {next} /^Path/ {next} {mac=$2; ifnum=$3; ifstate=$4; name=$5; type=$8}'
    GET_IP4='{c="netstat -niwf inet | grep "name; c | getline; close(c); if (NF==10) {next} mtu=$2; IPv4=$4; RXbytes=$5; TXbytes=$7; collisions=$9}'
    GET_IP6='{c="netstat -niwf inet6 | grep "name" "; c| getline; close(c); IPv6=$3}'
    GET_SPEED_DUPLEX='{c="lanadmin -x "ifnum ; c | getline; close(c); if (NF==4) speed=$3"Mb/s"; sub("\-.*", "", $4); duplex=tolower($4)}'
    PRINTF='{printf "%-10s %-17s  %-15s  %-42s %-10s  %-16s %-16s %-12s %-12s\n", name, mac, IPv4, IPv6, collisions, RXbytes, TXbytes, speed, duplex}'
    echo "$HEADER"
    $CMD | awk "$LANSCAN_AWK $GET_IP4 $GET_IP6 $GET_SPEED_DUPLEX $PRINTF"
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	assertHaveCommand ifconfig
	assertHaveCommand netstat

	CMD_LIST_INTERFACES='ifconfig -a'
	CHOOSE_ACTIVE='/LOOPBACK/ {next} !/RUNNING/ {next} /^[a-z0-9]+: / {sub(":$", "", $1); print $1}'
	GET_MAC='{$1 == "ether" && mac = $2}'
	GET_IP='/ netmask / {for (i=1; i<=NF; i++) {if ($i == "inet") IPv4 = $(i+1); if ($i == "inet6") IPv6 = $(i+1)}}'
	GET_SPEED_DUPLEX='/media: / {sub("\134(", "", $4); speed=$4; sub("-duplex.*", "", $5); sub("<", "", $5); duplex=$5}'
	GET_RXbytes_TXbytes_COLLISIONS='(NF==11) {if ($4 == mac) {RXbytes = $7; TXbytes = $10; collisions = $11}}'
	FILL_BLANKS='{IPv4 = IPv4 ? IPv4 : "<n/a>"; IPv6 = IPv6 ? IPv6 : "<n/a>"}'
	GET_ALL="$GET_MAC $GET_IP $GET_SPEED_DUPLEX $GET_RXbytes_TXbytes_COLLISIONS $FILL_BLANKS"

	echo "$HEADER"
	for iface in `$CMD_LIST_INTERFACES | tee $TEE_DEST | awk "$CHOOSE_ACTIVE"`
	do
		echo "Cmd = [$CMD_LIST_INTERFACES];  | awk '$CHOOSE_ACTIVE'" >> $TEE_DEST
		CMD_DESCRIBE_INTERFACE="eval ifconfig $iface ; netstat -b -I $iface"
		$CMD_DESCRIBE_INTERFACE | tee -a $TEE_DEST | awk "$GET_ALL $PRINTF" name=$iface 
		echo "Cmd = [$CMD_DESCRIBE_INTERFACE];     | awk '$GET_ALL $PRINTF' name=$iface" >> $TEE_DEST
	done
fi
