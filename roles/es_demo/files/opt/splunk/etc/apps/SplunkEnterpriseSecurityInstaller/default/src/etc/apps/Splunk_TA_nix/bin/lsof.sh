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

HEADER='COMMAND     PID        USER   FD      TYPE             DEVICE     SIZE       NODE NAME'
HEADERIZE='{NR == 1 && $0 = header}'
CMD='lsof -nPs'
PRINTF='{printf "%-15.15s  %-10s  %-15.15s  %-8s %-8s  %-15.15s  %15s  %-20.20s  %-s\n", $1,$2,$3,$4,$5,$6,$7,$8,$9}'

if [ "x$KERNEL" = "xLinux" ] ; then
	FILTER='/Permission denied/ {next} {if ($4 == "NOFD" || $5 == "unknown") next}'
	FILL_BLANKS='{if (NF<9) {node=$7; name=$8; $7="?"; $8=node; $9=name}}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    FILTER='/Permission denied/ {next} {if ($4 == "NOFD" || $5 == "unknown") next}'
    FILL_BLANKS='{if (NF<9) {node=$7; name=$8; $7="?"; $8=node; $9=name}}'
elif [ "x$KERNEL" = "xSunOS" ] ; then
	failUnsupportedScript
elif [ "x$KERNEL" = "xAIX" ] ; then
	failUnsupportedScript
elif [ "x$KERNEL" = "xDarwin" ] ; then
	FILTER='{if ($5 ~ /KQUEUE|PIPE|PSXSEM/) next}'
	FILL_BLANKS='{if (NF<9) {name=$8; $8="?"; $9=name}}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	failUnsupportedScript
fi

assertHaveCommand $CMD
$CMD 2>$TEE_DEST | tee $TEE_DEST | awk "$HEADERIZE $FILTER $FILL_BLANKS $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD 2>$TEE_DEST];  | awk '$HEADERIZE $FILTER $FILL_BLANKS $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
