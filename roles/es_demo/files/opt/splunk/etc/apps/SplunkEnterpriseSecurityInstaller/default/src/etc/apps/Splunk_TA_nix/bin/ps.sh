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

HEADER='USER               PID   PSR   pctCPU       CPUTIME  pctMEM     RSZ_KB     VSZ_KB   TTY      S       ELAPSED  COMMAND             ARGS'
FORMAT='{sub("^_", "", $1); if (NF>12) {args=$13; for (j=14; j<=NF; j++) args = args "_" $j} else args="<noArgs>"; sub("^[^\134[: -]*/", "", $12)}'
NORMALIZE='(NR>1) {if ($4<0 || $4>100) $4=0; if ($6<0 || $6>100) $6=0}'
PRINTF='{if (NR == 1) {print $0} else {printf "%-14.14s  %6s  %4s   %6s  %12s  %6s   %8s   %8s   %-7.7s  %1.1s  %12s  %-18.18s  %s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, args}}'

HEADERIZE='{NR == 1 && $0 = header}'
CMD='ps auxww'

if [ "x$KERNEL" = "xLinux" ] ; then
	assertHaveCommand ps
	CMD='ps -wweo uname,pid,psr,pcpu,cputime,pmem,rsz,vsz,tty,s,etime,args'
elif [ "x$KERNEL" = "xSunOS" ] ; then
	assertHaveCommandGivenPath /usr/bin/ps
	CMD='/usr/bin/ps -eo user,pid,psr,pcpu,time,pmem,rss,vsz,tty,s,etime,args'
elif [ "x$KERNEL" = "xAIX" ] ; then
	assertHaveCommandGivenPath /usr/sysv/bin/ps
	CMD='/usr/sysv/bin/ps -eo user,pid,psr,pcpu,time,pmem,rss,vsz,tty,s,etime,args'
	FORMAT='{sub("^_", "", $1); if (NF>12) {args=$13; for (j=14; j<=NF; j++) args = args "_" $j} else args="<noArgs>"; sub("^.*/|:|-", "", $12)}'
	# replace the tail ( ; sub("^[^\134[: -]*/", "", $12)}' ) of above can't be run
elif [ "x$KERNEL" = "xDarwin" ] ; then
	assertHaveCommand ps
	CMD='ps axo ruser,pid,pcpu,cputime,pmem,rss,vsz,tty,state,etime,command'
	FILL_BLANKS='{if (NR>1) {for (i=NF; i>2; i--) $(i+1) = $i; $3 = "?"}}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    assertHaveCommand ps
    export UNIX95=1
    CMD='ps -e -o ruser,pid,pset,pcpu,time,vsz,tty,state,etime,args'
    FORMAT='{sub("^_", "", $1); if (NF>12) {args=$13; for (j=14; j<=NF; j++) args = args "_" $j} else args="<noArgs>"; sub("^[\[\]]", "", $11)}'
    PRINTF='{if (NR == 1) {print $0} else {printf "%-14.14s  %6s  %4s   %6s  %12s  %6s   %8s   %8s   %-7.7s  %1.1s  %12s  %-18.18s  %s\n", $1, $2, $3, $4, $5, "?", "?", $6, $7, $8, $9, $10, $11, arg}}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	assertHaveCommand ps
	CMD='ps axo ruser,pid,pcpu,cputime,pmem,rss,vsz,tty,state,etime,command'
	FILL_BLANKS='{if (NR>1) {for (i=NF; i>2; i--) $(i+1) = $i; $3 = "?"}}'
fi

$CMD | tee $TEE_DEST | $AWK "$HEADERIZE $FILL_BLANKS $FORMAT $NORMALIZE $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FILL_BLANKS $FORMAT $NORMALIZE $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
