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

HEADER='CPU    pctUser    pctNice  pctSystem  pctIowait    pctIdle'
HEADERIZE="BEGIN {print \"$HEADER\"}"
PRINTF='{printf "%-3s  %9s  %9s  %9s  %9s  %9s\n", cpu, pctUser, pctNice, pctSystem, pctIowait, pctIdle}'

if [ "x$KERNEL" = "xLinux" ] ; then
    queryHaveCommand sar
    FOUND_SAR=$?
    queryHaveCommand mpstat
    FOUND_MPSTAT=$?
    if [ $FOUND_SAR -eq 0 ] ; then
        CMD='sar -P ALL 1 1'
        FORMAT='{cpu=$3; pctUser=$4; pctNice=$5; pctSystem=$6; pctIowait=$7; pctIdle=$NF}'
    elif [ $FOUND_MPSTAT -eq 0 ] ; then
        CMD='mpstat -P ALL 1 1'
        FORMAT='{cpu=$(NF-9); pctUser=$(NF-8); pctNice=$(NF-7); pctSystem=$(NF-6); pctIowait=$(NF-5); pctIdle=$(NF-1)}'
    else
        failLackMultipleCommands sar mpstat
    fi
    FILTER='/Average|Linux|^$|%/ {next} (NR==1) {next}'
elif [ "x$KERNEL" = "xSunOS" ] ; then
    if [ $SOLARIS_8 -o $SOLARIS_9 ] ; then
        CMD='eval mpstat -p 1 1; mpstat -a -p 1 1 | tail -1 | sed "s/^[ ]*0/all/"'
    else
        CMD='eval mpstat -q -p 1 1; mpstat -aq -p 1 1 | tail -1 | sed "s/^[ ]*0/all/"'
    fi
    assertHaveCommand $CMD
    FILTER='(NR<2) {next}'
    FORMAT='{cpu=$1; pctUser=$(NF-4); pctNice="0"; pctSystem=$(NF-3); pctIowait=$(NF-2); pctIdle=$(NF-1)}'
elif [ "x$KERNEL" = "xAIX" ] ; then
    queryHaveCommand sar
    FOUND_SAR=$?
    if [ $FOUND_SAR -eq 0 ] ; then
        CMD='sar -P ALL 1 1'
    FORMAT='{k=0;if(NR==7) k=1} {sub("^-", "all", $1); cpu=$(1+k); pctUser=$(2+k); pctNice="0"; pctSystem=$(3+k); pctIowait=$(4+k); pctIdle=$(5+k)}'
    fi
    FILTER='/System|AIX|^$|%/ {next}'
elif [ "x$KERNEL" = "xDarwin" ] ; then
    CMD='sar -u 1'
    assertHaveCommand $CMD
    FILTER='($0 !~ "Average") {next}'
    FORMAT='{cpu="all"; pctUser=$2; pctNice=$3; pctSystem=$4; pctIdle=$5; pctIowait="0"}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
    CMD='iostat -C -c 2'
    assertHaveCommand $CMD
    FILTER='(NR<4) {next}'
    FORMAT='{cpu="all"; pctUser=$(NF-4); pctNice=$(NF-3); pctSystem=$(NF-2); pctIdle=$NF; pctIowait="0"}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    queryHaveCommand sar
    FOUND_SAR=$?
    if [ $FOUND_SAR -eq 0 ] ; then
        CMD='sar -M 1 1 ALL'
    fi
    FILTER='/HP-UX|^$|%/ {next}'
    FORMAT='{k=0; if(5<NF) k=1} {cpu=$(1+k); pctUser=$(2+k); pctNice="0"; pctSystem=$(3+k); pctIowait=$(4+k); pctIdle=$(5+k)}'
fi

$CMD | tee $TEE_DEST | $AWK "$HEADERIZE $FILTER $FORMAT $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FILTER $FORMAT $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
