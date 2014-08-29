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

HEADER='memTotalMB   memFreeMB   memUsedMB  memFreePct  memUsedPct   pgPageOut  swapUsedPct   pgSwapOut   cSwitches  interrupts       forks   processes     threads  loadAvg1mi'
HEADERIZE="BEGIN {print \"$HEADER\"}"
PRINTF='END {printf "%10d  %10d  %10d  %10.1f  %10.1f  %10s   %10.1f  %10s  %10s  %10s  %10s  %10s  %10s  %10.2f\n", memTotalMB, memFreeMB, memUsedMB, memFreePct, memUsedPct, pgPageOut, swapUsedPct, pgSwapOut, cSwitches, interrupts, forks, processes, threads, loadAvg1mi}'
DERIVE='END {memUsedMB=memTotalMB-memFreeMB; memUsedPct=(100.0*memUsedMB)/memTotalMB; memFreePct=100.0-memUsedPct; swapUsedPct=swapUsed ? (100.0*swapUsed)/(swapUsed+swapFree) : 0}'

if [ "x$KERNEL" = "xLinux" ] ; then
	assertHaveCommand uptime
	assertHaveCommand ps
	assertHaveCommand vmstat
	CMD='eval uptime ; ps -e | wc -l ; ps -eT | wc -l ; vmstat -s'
	PARSE_0='NR==1 {loadAvg1mi=0+$(NF-2)} NR==2 {processes=$1} NR==3 {threads=$1}'
	PARSE_1='/total memory$/ {memTotalMB=$1/1024} /free memory$/ {memFreeMB+=$1/1024} /buffer memory$/ {memFreeMB+=$1/1024} /swap cache$/ {memFreeMB+=$1/1024}'
	PARSE_2='/pages paged out$/ {pgPageOut=$1} /used swap$/ {swapUsed=$1} /free swap$/ {swapFree=$1} /pages swapped out$/ {pgSwapOut=$1}'
	PARSE_3='/interrupts$/ {interrupts=$1} /CPU context switches$/ {cSwitches=$1} /forks$/ {forks=$1}'
	MASSAGE="$PARSE_0 $PARSE_1 $PARSE_2 $PARSE_3 $DERIVE"
elif [ "x$KERNEL" = "xSunOS" ] ; then
	assertHaveCommand vmstat
	assertHaveCommandGivenPath /usr/sbin/swap
	assertHaveCommandGivenPath /usr/sbin/prtconf
	assertHaveCommand prstat
	if [ $SOLARIS_8 -o $SOLARIS_9 ] ; then
		CMD='eval /usr/sbin/prtconf 2>/dev/null | grep Memory ; /usr/sbin/swap -s ; vmstat    1 1 ; vmstat -s ; prstat -n 1 1 1'
	else
		CMD='eval /usr/sbin/prtconf 2>/dev/null | grep Memory ; /usr/sbin/swap -s ; vmstat -q 1 1 ; vmstat -s ; prstat -n 1 1 1'
	fi
	PARSE_0='/^Memory size:/ {memTotalMB=$3} (NR==5) {memFreeMB=$5 / 1024}'
	PARSE_1='(NR==2) {swapUsed=0+$(NF-3); swapFree=0+$(NF-1)}'
	PARSE_2='/pages paged out$/ {pgPageOut=$1} /pages swapped out$/ {pgSwapOut=$1}'
	PARSE_3='/cpu context switches$/ {cSwitches=$1} /device interrupts$/ {interrupts=$1} / v?forks$/ {forks+=$1}'
	PARSE_4='/^Total: / {processes=$2; threads=$4; loadAvg1mi=0+$(NF-2)}'
	MASSAGE="$PARSE_0 $PARSE_1 $PARSE_2 $PARSE_3 $PARSE_4 $DERIVE"
elif [ "x$KERNEL" = "xAIX" ] ; then
	assertHaveCommand uptime
	assertHaveCommand ps
	assertHaveCommand vmstat
	assertHaveCommandGivenPath /usr/sbin/swap
	assertHaveCommandGivenPath /usr/bin/svmon
	CMD='eval uptime ; ps -e | wc -l ; ps -em | wc -l ; /usr/sbin/swap -s ; vmstat    1 1 ; vmstat -s ; svmon'
	PARSE_0='NR==1 {loadAvg1mi=0+$(NF-2)} NR==2 {processes=$1} NR==3 {threads=$1-processes }'
        # ps -em inclundes processes with there threads ( at least one), so processes must be excluded to count threads #
	PARSE_1='(NR==4) {swapUsed=0+$(NF-5); swapFree=0+$(NF-1)}'
	PARSE_2='/^memory / {memTotalMB=$2 / 256 ; memFreeMB=$4 / 256}'
	PARSE_3='/paging space page outs$/ {pgPageOut=$1 ; pgSwapOut="?" }'
        # no pgSwapOut parameter and can't be monitored in AIX (by Jacky Ho, Systex)
	PARSE_4='/cpu context switches$/ {cSwitches=$1} /device interrupts$/ {interrupts=$1 ; forks="?" }'
	MASSAGE="$PARSE_0 $PARSE_1 $PARSE_2 $PARSE_3 $PARSE_4 $DERIVE"
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    assertHaveCommand uptime
    assertHaveCommand ps
    assertHaveCommand swapinfo
    assertHaveCommand vmstat
    CMD='eval uptime ; ps -e | wc -l ; swapinfo -m; vmstat -f; vmstat -s'
    PARSE_0='NR==1 {loadAvg1mi=0+$(NF-2)} NR==2 {processes=$1} {threads="?"}'
    PARSE_1='NR==5 {swapUsed=$3; swapFree=$4}'
    PARSE_2='NR==7 {memTotalMB=$2; memUsedMB=$3; memFreeMB=$4}'
    PARSE_3='NR==8 {forks=$1}'
    PARSE_4='/pages paged out$/ {pgPageOut=$1} /pages swapped out$/ {pgSwapOut=$1}'
    PARSE_5='/interrupts$/ {interrupts=$1} /cpu context switches$/ {cSwitches=$1} /forks$/ {forks=$1}'
    MASSAGE="$PARSE_0 $PARSE_1 $PARSE_2 $PARSE_3 $PARSE_4 $PARSE_5 $DERIVE"
elif [ "x$KERNEL" = "xDarwin" ] ; then
	assertHaveCommand sysctl
	assertHaveCommand top
	CMD='eval sysctl hw.memsize ; sysctl vm.swapusage ; top -l 1 -n 0'
	FUNCS='function toMB(s) {n=0+s; if (index(s,"K")) {n /= 1024} if (index(s,"G")) {n *= 1024} return n}'
	PARSE_0='/^hw.memsize:/ {memTotalMB=$2 / (1024*1024)}'
	PARSE_1='/^PhysMem:/ {memFreeMB=toMB($6)+toMB($10)}' # we count "inactive" as "free", since it can be made available w/o a pagein/swapin
	PARSE_2='/^vm.swapusage:/ {swapUsed=toMB($7); swapFree=toMB($10)}'
	PARSE_3='/^VM:/ {pgPageOut=0+$7}'
	if $OSX_GE_SNOW_LEOPARD; then
		PARSE_4='/^Processes:/ {processes=$2; threads=$(NF-1)}'
	else
		PARSE_4='/^Processes:/ {processes=$2; threads=$(NF-2)}'
	fi
	PARSE_5='/^Load Avg:/ {loadAvg1mi=0+$3}'
	MASSAGE="$FUNCS $PARSE_0 $PARSE_1 $PARSE_2 $PARSE_3 $PARSE_4 $PARSE_5 $DERIVE"
	FILL_BLANKS='END {pgSwapOut=cSwitches=interrupts=forks="?"}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	CMD='eval sysctl hw.physmem ; vmstat -s ; top -Sb 0'
	FUNCS='function toMB(s) {n=0+s; if (index(s,"K")) {n /= 1024} if (index(s,"G")) {n *= 1024} return n}'
	PARSE_0='(NR==1) {memTotalMB=$2 / (1024*1024)}'
	PARSE_1='/pager pages paged out$/ {pgPageOut+=$1} /fork\(\) calls$/ {forks+=$1} /cpu context switches$/ {cSwitches+=$1} /interrupts$/ {interrupts+=$1}'
	PARSE_2='/load averages:/ {loadAvg1mi=$6} /^[0-9]+ processes: / {processes=$1}'
	PARSE_3='/^Swap: / {swapUsed=toMB($4); swapFree=toMB($6)} /^Mem: / {memFreeMB=toMB($4)+toMB($12)}'
	MASSAGE="$FUNCS $PARSE_0 $PARSE_1 $PARSE_2 $PARSE_3 $DERIVE"
	FILL_BLANKS='END {threads=pgSwapOut="?"}'
fi

$CMD | tee $TEE_DEST | $AWK "$HEADERIZE $MASSAGE $FILL_BLANKS $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $MASSAGE $FILL_BLANKS $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
