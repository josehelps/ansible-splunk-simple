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

# a similar effect can be accomplished with: "nc -z 127.0.0.1 1-32768", and "nc -zu 127.0.0.1 1-32768"

. `dirname $0`/common.sh

HEADER='Proto   Port'
HEADERIZE="BEGIN {print \"$HEADER\"}"
PRINTF='{printf "%-5s  %5d\n", proto, port}'
FILTER_INACTIVE='($NF ~ /^CLOSE/) {next}'

if [ "x$KERNEL" = "xLinux" ] ; then
	CMD='eval netstat -ln | egrep "^tcp|^udp"'
	FORMAT='{proto=$1; sub("^.*:", "", $4); port=$4}'
elif [ "x$KERNEL" = "xSunOS" ] ; then
	CMD='netstat -an -f inet -f inet6'
	FIGURE_SECTION='BEGIN {inUDP=1;inTCP=0} /^TCP: IPv/ {inUDP=0;inTCP=1} /^SCTP:/ {exit}'
	FILTER='/: IPv|Local Address|^$|^-----/ {next} (! port) {next}'
	FORMAT='{if (inUDP) proto="udp"; if (inTCP) proto="tcp"; sub("^.*[^0-9]", "", $1); port=$1}'
elif [ "x$KERNEL" = "xAIX" ] ; then
	CMD='eval netstat -an | egrep "^tcp|^udp"'
	HEADERIZE="BEGIN {print \"$HEADER\"}"
	FORMAT='{gsub("[46]", "", $1); proto=$1; sub("^.*[^0-9]", "", $4); port=$4}'
	FILTER='{if ($4 == "") next}'
elif [ "x$KERNEL" = "xDarwin" ] ; then
	CMD='eval netstat -ln | egrep "^tcp|^udp"'
	HEADERIZE="BEGIN {print \"$HEADER\"}"
	FORMAT='{gsub("[46]", "", $1); proto=$1; sub("^.*[^0-9]", "", $4); port=$4}'
	FILTER='{if ($4 == "") next}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    CMD='eval netstat -an | egrep "^tcp|^udp"'
    HEADERIZE="BEGIN {print \"$HEADER\"}"
    FORMAT='{gsub("[46]", "", $1); proto=$1; sub("^.*[^0-9]", "", $4); port=$4}'
    FILTER='{if ($4 == "") next}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	CMD='eval netstat -ln | egrep "^tcp|^udp"'
	HEADERIZE="BEGIN {print \"$HEADER\"}"
	FORMAT='{gsub("[46]", "", $1); proto=$1; sub("^.*[^0-9]", "", $4); port=$4}'
fi

assertHaveCommand $CMD
$CMD | tee $TEE_DEST | $AWK "$HEADERIZE $FIGURE_SECTION $FORMAT $FILTER $FILTER_INACTIVE $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FIGURE_SECTION $FORMAT $FILTER $FILTER_INACTIVE $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
