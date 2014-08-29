#!/bin/sh                                                                                                
# Copyright 2005-2013 Splunk, Inc.                                                                       
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

if [ "x$KERNEL" = "xLinux" ] ; then
	assertHaveCommand date
	assertHaveCommand yum
	
	CMD='eval date ; yum check-update'
	
	PARSE_0='NR==1 {
		DATE=$0
		PROCESS=0
		UPDATES["addons"]=0
		UPDATES["base"]=0
		UPDATES["extras"]=0
		UPDATES["updates"]=0
	}'

	# Skip extraneous text up to first blank line.
	PARSE_1='NR>1 && PROCESS==0 && $0 ~ /^[[:blank:]]*$|^$/ {
		PROCESS=1
	}'

	PARSE_2='NR>1 && PROCESS==1 {
		num = split($0, update_array)
		if (num == 3) {
			# Record the update count
			UPDATES[update_array[3]] = UPDATES[update_array[3]]+1
			printf "%s package=\"%s\" package_type=\"%s\"\n", DATE, update_array[1], update_array[3]		
		} else if (num==2 && update_array[1] != "") {
			printf "%s package=\"%s\"\n", DATE, update_array[1]
		}
	}'
		
	PARSE_3='END {
		TOTALS=""
		for (key in UPDATES) {
			TOTALS=TOTALS key "=" UPDATES[key] " "
		}
		printf "%s %s\n", DATE, TOTALS
	}'
	
	MASSAGE="$PARSE_0 $PARSE_1 $PARSE_2 $PARSE_3"

elif [ "x$KERNEL" = "xDarwin" ] ; then
	assertHaveCommand date	
	assertHaveCommand softwareupdate
	
	CMD='eval date ; softwareupdate -l'
	
	PARSE_0='NR==1 {
		DATE=$0
		PROCESS=0
		TOTAL=0
	}'
	
	# If the first non-space character is an asterisk, assume this is the name
	# of the update. Otherwise, print the update.
	PARSE_1='NR>1 && PROCESS==1 && $0 !~ /^[[:blank:]]*$/ {
		if ( $0 ~ /^[[:blank:]]*\*/ ) {
			PACKAGE="package=\"" $2 "\""
			RECOMMENDED=""
			RESTART=""
			TOTAL=TOTAL+1
		} else {
			if ( $0 ~ /recommended/ ) { RECOMMENDED="is_recommended=\"true\"" }
			if ( $0 ~ /restart/ ) { RESTART="restart_required=\"true\"" }
			printf "%s %s %s %s\n", DATE, PACKAGE, RECOMMENDED, RESTART
		}
	}'

	# Use sentinel value to skip all text prior to update list.
	PARSE_2='NR>1 && PROCESS==0 && $0 ~ /found[[:blank:]]the[[:blank:]]following/ { 
		PROCESS=1
	}'
	
	PARSE_3='END {
		printf "%s total_updates=%s\n", DATE, TOTAL
	}'
	
	MASSAGE="$PARSE_0 $PARSE_1 $PARSE_2 $PARSE_3"
	
else
	# Exits
	failUnsupportedScript
fi

$CMD | tee $TEE_DEST | $AWK "$MASSAGE"
echo "Cmd = [$CMD];  | $AWK '$MASSAGE'" >> $TEE_DEST
