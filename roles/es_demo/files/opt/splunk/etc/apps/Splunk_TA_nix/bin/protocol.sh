#!/bin/sh                                                                                                
# Copyright 2009-2011 Splunk, Inc.                                                                       
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

CMD='netstat -s'
HEADER='  IPdropped   TCPrexmits   TCPreorder   TCPpktRecv   TCPpktSent   UDPpktLost   UDPunkPort   UDPpktRecv   UDPpktSent'
HEADERIZE="BEGIN {print \"$HEADER\"}"
PRINTF='END {printf " %10d   %10d   %10d   %10d   %10d   %10d   %10d   %10d   %10d\n", IPdropped, TCPrexmits, TCPreorder, TCPpktRecv, TCPpktSent, UDPpktLost, UDPunkPort, UDPpktRecv, UDPpktSent}'

if [ "x$KERNEL" = "xLinux" ] ; then
	FIGURE_SECTION='/^Ip:$/ {inIP=1;inTCP=0;inUDP=0} /^Tcp(Ext)?:$/ {inIP=0;inTCP=1;inUDP=0} /^Udp:$/ {inIP=0;inTCP=0;inUDP=1} {if (NF==1 && $1 !~ /^Ip:$|^Udp:$|^Tcp(Ext)?:$/) inIP=inTCP=inUDP=0}'
	SECTION_IP='inIP && /outgoing packets dropped/ {IPdropped=$1}'
	SECTION_TCP='inTCP && /segments retransmited/ {TCPrexmits=$1} inTCP && /Detected reordering/ {TCPreorder=$3} inTCP && /[0-9] segments received$/ {TCPpktRecv=$1} inTCP && /segments send out/ {TCPpktSent=$1}'
	SECTION_UDP='inUDP && /packets received/ {UDPpktRecv=$1} inUDP && /packets sent/ {UDPpktSent=$1} inUDP && /packet receive errors/ {UDPpktLost=$1} inUDP && /packets to unknown port received/ {UDPunkPort=$1}'
elif [ "x$KERNEL" = "xSunOS" ] ; then
	COMMON='{gsub("=", "", $0)}'
	SECTION_IP='/ipOutDiscards/ {IPdropped+=$2} /ipOutNoRoutes/ {IPdropped+=$4} /ipv6OutNoRoutes/ {IPdropped+=$2} /ipv6OutDiscards/ {IPdropped+=$4}'
	SECTION_TCP='/tcpRetransSegs/ {TCPrexmits=$2} /tcpInUnorderSegs/ {TCPreorder=$2} /tcpInSegs/ {TCPpktRecv=$2} /tcpOutSegs/ {TCPpktSent=$4}'
	SECTION_UDP='/udpOutErrors/ {UDPpktLost=$4} /udpInErrors/ {UDPunkPort=$5} /udpInDatagrams/ {UDPpktRecv=$3} /udpOutDatagrams/ {UDPpktSent=$2}'
elif [ "x$KERNEL" = "xAIX" ] ; then
	FIGURE_SECTION='/^ip:$/ {inIP=1;inTCP=0;inUDP=0} /^tcp:$/ {inIP=0;inTCP=1;inUDP=0} /^udp:$/ {inIP=0;inTCP=0;inUDP=1} {if (NF==1 && $1 !~ /^ip:$|^udp:$|^tcp:$/) inIP=inTCP=inUDP=0}'
	SECTION_IP='inIP && /output packets? (dropped|discarded)/ {IPdropped+=$1}'
	SECTION_TCP='inTCP && /data packet.* bytes\) retransmitted$/ {TCPrexmits=$1} inTCP && /out-of-order packets?/ {TCPreorder=$1} inTCP && /packets? received$/ {TCPpktRecv=$1} inTCP && /packets? sent/ {TCPpktSent=$1}'
	SECTION_UDP='inUDP && /datagrams? received$/ {UDPpktRecv=$1} inUDP && /datagrams? output$/ {UDPpktSent=$1} inUDP && /dropped due to full socket buffers$/ {UDPpktLost=$1} inUDP && /dropped due to no socket$/ {UDPunkPort=$1}'
elif [ "x$KERNEL" = "xDarwin" ] ; then
	FIGURE_SECTION='/^ip:$/ {inIP=1;inTCP=0;inUDP=0} /^tcp:$/ {inIP=0;inTCP=1;inUDP=0} /^udp:$/ {inIP=0;inTCP=0;inUDP=1} {if (NF==1 && $1 !~ /^ip:$|^udp:$|^tcp:$/) inIP=inTCP=inUDP=0}'
	SECTION_IP='inIP && /output packets? (dropped|discarded)/ {IPdropped+=$1}'
	SECTION_TCP='inTCP && /data packets? .* retransmitted/ {TCPrexmits=$1} inTCP && /out-of-order packets?/ {TCPreorder=$1} inTCP && /packets? received$/ {TCPpktRecv=$1} inTCP && /packets? sent/ {TCPpktSent=$1}'
	SECTION_UDP='inUDP && /datagrams? received$/ {UDPpktRecv=$1} inUDP && /datagrams? output$/ {UDPpktSent=$1} inUDP && /dropped due to full socket buffers$/ {UDPpktLost=$1} inUDP && /dropped due to no socket$/ {UDPunkPort=$1}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    FIGURE_SECTION='/^ip:$/ {inIP=1;inTCP=0;inUDP=0} /^tcp(Ext)?:$/ {inIP=0;inTCP=1;inUDP=0} /^udp:$/ {inIP=0;inTCP=0;inUDP=1} {if (NF==1 && $1 !~ /^ip:$|^udp:$|^tcp(Ext)?:$/) inIP=inTCP=inUDP=0}'
    SECTION_IP='inIP && /fragments dropped/ {IPdropped=$1}'
    SECTION_TCP='inTCP && /retransmited$/ {TCPrexmits=$1} inTCP && /out of order/ {TCPreorder=$1} inTCP && /[0-9] packets received$/ {TCPpktRecv=$1} inTCP && /[0-9] packets sent$/ {TCPpktSent=$1}'
    SECTION_UDP='inUDP && /packets received/ {UDPpktRecv=$1} inUDP && /packets sent/ {UDPpktSent=$1} inUDP && /packet receive errors/ {UDPpktLost=$1} inUDP && /packets to unknown port received/ {UDPunkPort=$1}'
 elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	FIGURE_SECTION='/^ip:$/ {inIP=1;inTCP=0;inUDP=0} /^tcp:$/ {inIP=0;inTCP=1;inUDP=0} /^udp:$/ {inIP=0;inTCP=0;inUDP=1} {if (NF==1 && $1 !~ /^ip:$|^udp:$|^tcp:$/) inIP=inTCP=inUDP=0}'
	SECTION_IP='inIP && /output packets? (dropped|discarded)/ {IPdropped+=$1}'
	SECTION_TCP='inTCP && /data packet.* bytes\) retransmitted$/ {TCPrexmits=$1} inTCP && /out-of-order packets?/ {TCPreorder=$1} inTCP && /packets? received$/ {TCPpktRecv=$1} inTCP && /packets? sent/ {TCPpktSent=$1}'
	SECTION_UDP='inUDP && /datagrams? received$/ {UDPpktRecv=$1} inUDP && /datagrams? output$/ {UDPpktSent=$1} inUDP && /dropped due to full socket buffers$/ {UDPpktLost=$1} inUDP && /dropped due to no socket$/ {UDPunkPort=$1}'
fi

assertHaveCommand $CMD
$CMD | tee $TEE_DEST | $AWK "$HEADERIZE $FIGURE_SECTION $COMMON $SECTION_IP $SECTION_TCP $SECTION_UDP $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FIGURE_SECTION $COMMON $SECTION_IP $SECTION_TCP $SECTION_UDP $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
