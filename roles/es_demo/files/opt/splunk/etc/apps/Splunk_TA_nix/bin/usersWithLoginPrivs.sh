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

HEADER='USERNAME                        HOME_DIR                                                      USER_INFO'
HEADERIZE="BEGIN {print \"$HEADER\"}"

CMD='cat /etc/passwd'
AWK_IFS='-F:'

FILTER='($NF !~ /sh$/) {next}'
PRINTF='{printf "%-30.30s  %-60.60s  %s\n", $1, $6, $5}'

if [ "x$KERNEL" = "xLinux" ] ; then
	FILL_BLANKS='{$5 || $5 = "?"}'
elif [ "x$KERNEL" = "xSunOS" ] ; then
	FILL_BLANKS='{$5 || $5 = "?"}'
elif [ "x$KERNEL" = "xAIX" ] ; then
	FILL_BLANKS='{$5 || $5 = "?"}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
	FILL_BLANKS='{$5 || $5 = "?"}'
elif [ "x$KERNEL" = "xDarwin" ] ; then
	CMD='dscacheutil -q user'
	AWK_IFS=''
	MASSAGE='/^name: / {username = $2} /^dir: / {homeDir = $2} /^shell: / {shell = $2} /^gecos: / {userInfo = $2; for (i=3; i<=NF; i++) userInfo = userInfo " " $i} !/^gecos: / {next}'
	FILTER='{if (shell !~ /sh$/) next; if (homeDir ~ /^[0-9]+$/) next}'
	PRINTF='{printf "%-30.30s  %-60.60s  %s\n", username, length(homeDir) ? homeDir : "?", userInfo}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	FILL_BLANKS='{$5 || $5 = "?"}'
fi

assertHaveCommand $CMD
$CMD | tee $TEE_DEST | $AWK $AWK_IFS "$HEADERIZE $MASSAGE $FILTER $FILL_BLANKS $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK $AWK_IFS '$HEADERIZE $MASSAGE $FILTER $FILL_BLANKS $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
