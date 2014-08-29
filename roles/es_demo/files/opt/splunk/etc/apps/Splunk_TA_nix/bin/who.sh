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

CMD='who -H'
HEADER='USERNAME        LINE        HOSTNAME                                  TIME'
HEADERIZE='{NR == 1 && $0 = header}'
FORMAT='{length(hostname) || hostname=$NF; gsub("[)(]", "",hostname); time=$3; for (i=4; i<=lastTimeColumn; i++) time = time " " $i}'
PRINTF='{if (NR == 1) {print $0} else {printf "%-14s  %-10s  %-40.40s  %-s\n", $1,$2,hostname,time}}'

if [ "x$KERNEL" = "xLinux" ] ; then
	FILL_BLANKS='{hostname = ""; lastTimeColumn = NF-1; if (NF < 5) {hostname = "<console>"; lastTimeColumn = NF}}'
elif [ "x$KERNEL" = "xSunOS" ] ; then
	FILL_BLANKS='{hostname = ""; lastTimeColumn = NF-1; if (NF < 6) {hostname = "<console>"; lastTimeColumn = NF}}'
elif [ "x$KERNEL" = "xAIX" ] ; then
	FILL_BLANKS='{hostname = ""; lastTimeColumn = NF-1; if (NF < 6) {hostname = "<console>"; lastTimeColumn = NF}}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    CMD='who -HR'
    FILL_BLANKS='{hostname = ""; lastTimeColumn = NF-1; if (NF < 5) {hostname = "<console>"; lastTimeColumn = NF}}'
elif [ "x$KERNEL" = "xDarwin" ] ; then
	FILL_BLANKS='{hostname = ""; lastTimeColumn = NF-1; if (NF < 6) {hostname = "<console>"; lastTimeColumn = NF}}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	FILL_BLANKS='{hostname = ""; lastTimeColumn = NF-1; if (NF < 6) {hostname = "<console>"; lastTimeColumn = NF}}'
fi

assertHaveCommand $CMD
$CMD | tee $TEE_DEST | $AWK "$HEADERIZE $FILL_BLANKS $FORMAT $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FILL_BLANKS $FORMAT $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
