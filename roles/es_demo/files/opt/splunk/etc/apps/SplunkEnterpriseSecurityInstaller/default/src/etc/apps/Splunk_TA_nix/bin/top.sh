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

HEADER='   PID  USER              PR    NI    VIRT     RES     SHR   S  pctCPU  pctMEM       cpuTIME  COMMAND'
PRINTF='{printf "%6s  %-14s  %4s  %4s  %6s  %6s  %6s  %2s  %6s  %6s  %12s  %-s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12}'

CMD='top'

if [ "x$KERNEL" = "xLinux" ] ; then
	CMD='top -bn 1'
	FILTER='{if (NR < 7) next}'
	HEADERIZE='{NR == 7 && $0 = header}'
elif [ "x$KERNEL" = "xSunOS" ] ; then
	CMD='prstat -n 999 1 1'
	HEADERIZE="BEGIN {print \"$HEADER\"}"
	FILTER='(NR==1) {next} /^Total:|^$/ {exit}'
	FORMAT_DOMAIN='{virt=$3; res=$4; stateRaw=$5; pr=$6; ni=$7; cpuTIME=$8; pctCPU=0.0+$9; sub("/.*$", "", $10); command=$10 ? $10 : "<n/a>"}'
	SPECIFY_STATES_MAP='BEGIN {map["sleep"]="S"; map["stop"]="T"; map["zombie"]="Z"; map["wait"]="D"; map["cpu"]="R"}'
	MAP_STATE='{sub("[0-9]+$", "", stateRaw); state=map[stateRaw]}'
	FORMAT_RANGE='{$3=pr; $4=ni; $5=virt; $6=res; $7="?"; $8=state; $9=pctCPU; $10="?"; $11=cpuTIME; $12=command}'
	FORMAT="$FORMAT_DOMAIN $SPECIFY_STATES_MAP $MAP_STATE $FORMAT_RANGE"
elif [ "x$KERNEL" = "xAIX" ] ; then
	CMD="eval /usr/sysv/bin/ps -eo pid,user,pri,nice,vsz,rss,s,s,pcpu,pmem,time,comm"
	HEADERIZE="BEGIN {print \"$HEADER\"}"
	FILTER='/PID/{next}'
	FORMAT='{$7="?" ; sub("A","R",$8)}'
        # Substitute ? for temporary [field 7] &
        # Substitute R(running) for A(Active) on field 8 in AIX by Jacky Ho, Systex 
elif [ "x$KERNEL" = "xDarwin" ] ; then
	if $OSX_GE_SNOW_LEOPARD; then
		CMD="eval top -F -l 2 -ocpu -Otime -stats pid,username,vsize,rsize,rshrd,cpu,time,command"
		FORMAT='{gsub("[+-] ", " "); virt=$3; res=$4; shr=$5; pctCPU=$6; cpuTIME=$7; command=$8; $3="?"; $4="?"; $5=virt; $6=res; $7=shr; $8="?"; $9=pctCPU; $10="?"; $11=cpuTIME; $12=command}'
	else
		CMD="eval top -F -l 2 -ocpu -Otime -t -R -p '^aaaaa ^nnnnnnnnnnnnnnnnnn ^lllll ^jjjjj ^ccccc ^ddddd ^bbbbbbbbbbbbbbbbbbbbbbbbbbbbb'"
		FORMAT='{                    virt=$3; res=$4;         pctCPU=$5; cpuTIME=$6; command=$7; $3="?"; $4="?"; $5=virt; $6=res; $7="?"; $8="?"; $9=pctCPU; $10="?"; $11=cpuTIME; $12=command}'
	fi
	HEADERIZE="BEGIN {print \"$HEADER\"}"
	FILTER='/ %CPU / {reportOrd++; next} {if ((reportOrd < 2) || !length) next}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    assertHaveCommand ps
    HEADERIZE="BEGIN {print \"$HEADER\"}"
    FILTER='/PID/{next}'
    export UNIX95=1
    CMD='ps -e -o pid,user,pri,nice,vsz,state,pcpu,time,comm'
    PRINTF='{q="?"; printf "%6s  %-14s  %4s  %4s  %6s  %6s  %6s  %2s  %6s  %6s  %12s  %-s\n", $1, $2, $3, $4, $5, q, q, $6, $7, q, $8, $9}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	CMD='top -Sb 999'
	HEADERIZE="BEGIN {print \"$HEADER\"}"
	FILTER='(NR<=8) {next} /^$/ {next}'
	FORMAT_DOMAIN='{pr=$4; ni=$5; virt=$6; res=$7; stateRaw=$8; cpuTIME=$9; pctCPU=0+$10; command=$11}'
	SPECIFY_STATES_MAP='BEGIN {map["SLEEP"]="S"; map["STOP"]="T"; map["ZOMB"]="Z"; map["WAIT"]="D"; map["LOCK"]="D"; map["START"]="R"; map["RUN"]="R"; map["CPU"]="R"}'
	MAP_STATE='{sub("[0-9]+$", "", stateRaw); state=map[stateRaw]; state=state ? state : "?"}'
	FORMAT_RANGE='{$3=pr; $4=ni; $5=virt; $6=res; $7="?"; $8=state; $9=pctCPU; $10="?"; $11=cpuTIME; $12=command}'
	FORMAT="$FORMAT_DOMAIN $SPECIFY_STATES_MAP $MAP_STATE $FORMAT_RANGE"
fi

assertHaveCommand $CMD
$CMD | tee $TEE_DEST | $AWK "$HEADERIZE $FILTER $FORMAT $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FILTER $FORMAT $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
