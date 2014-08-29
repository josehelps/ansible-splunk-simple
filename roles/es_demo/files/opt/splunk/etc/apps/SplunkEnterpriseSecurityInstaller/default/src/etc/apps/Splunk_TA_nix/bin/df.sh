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

HEADER='Filesystem                                          Type              Size        Used       Avail      UsePct    MountedOn'
HEADERIZE='{if (NR==1) {$0 = header}}'
PRINTF='{printf "%-50s  %-10s  %10s  %10s  %10s  %10s    %s\n", $1, $2, $3, $4, $5, $6, $7}'

if [ "x$KERNEL" = "xLinux" ] ; then
	assertHaveCommand df
	CMD='df -TPh'
	FILTER_POST='($2 ~ /^(tmpfs)$/) {next}'
elif [ "x$KERNEL" = "xSunOS" ] ; then
	assertHaveCommandGivenPath /usr/bin/df
	if $SOLARIS_8; then
		CMD='eval /usr/bin/df -n ; /usr/bin/df -k'
		NORMALIZE='function fromKB(KB) {MB = KB/1024; if (MB<1024) return MB "M"; GB = MB/1024; if (GB<1024) return GB "G"; TB = GB/1024; return TB "T"} {$3=fromKB($3); $4=fromKB($4); $5=fromKB($5)}'
	else
		CMD='eval /usr/bin/df -n ; /usr/bin/df -h'
	fi
	FILTER_PRE='/libc_psr/ {next}'
	MAP_FS_TO_TYPE='/: / {fsTypes[$1] = $2; next}'
	HEADERIZE='/^Filesystem/ {print header; next}'
    BEGIN='BEGIN { FS = "[ \t]*:?[ \t]+" }'
	FORMAT='{size=$2; used=$3; avail=$4; usePct=$5; mountedOn=$6; $2=fsTypes[mountedOn]; $3=size; $4=used; $5=avail; $6=usePct; $7=mountedOn}'
	FILTER_POST='($2 ~ /^(devfs|ctfs|proc|mntfs|objfs|lofs|fd|tmpfs)$/) {next} ($1 == "/proc") {next}'
elif [ "x$KERNEL" = "xAIX" ] ; then
	assertHaveCommandGivenPath /usr/bin/df
	CMD='eval /usr/sysv/bin/df -n ; /usr/bin/df -kP'
	NORMALIZE='function fromKB(KB) {MB = KB/1024; if (MB<1024) return MB "M"; GB = MB/1024; if (GB<1024) return GB "G"; TB = GB/1024; return TB "T"} {$3=fromKB($3); $4=fromKB($4); $5=fromKB($5)}'
	MAP_FS_TO_TYPE='/: / {fsTypes[$1] = $3; next}'
	HEADERIZE='/^Filesystem/ {print header; next}'
    FORMAT='{size=$2; used=$3; avail=$4; usePct=$5; mountedOn=$6; $2=fsTypes[mountedOn]; $3=size; $4=used; $5=avail; $6=usePct; $7=mountedOn; if ($2=="") {$2="?"}}'
	FILTER_POST='($2 ~ /^(proc)$/) {next} ($1 == "/proc") {next}'
elif [ "x$KERNEL" = "xHP-UX" ] ; then
    assertHaveCommand df
    assertHaveCommand fstyp
    CMD='df -Pk'
    MAP_FS_TO_TYPE='{c="fstyp " $1; c | getline ft; close(c);}'
    HEADERIZE='/^Filesystem/ {print header; next}'
    FORMAT='{size=$2; used=$3; avail=$4; usePct=$5; mountedOn=$6; $2=ft; $3=size; $4=used; $5=avail; $6=usePct; $7=mountedOn}'
    FILTER_POST='($2 ~ /^(tmpfs)$/) {next}'
elif [ "x$KERNEL" = "xDarwin" ] ; then
	assertHaveCommand mount
	assertHaveCommand df
	CMD='eval mount -t nocddafs,autofs,devfs,fdesc,nfs; df -h -T nocddafs,autofs,devfs,fdesc,nfs'
	MAP_FS_TO_TYPE='/ on / {fs=$1; sub("^.*\134(", "", $0); sub(",.*$", "", $0); fsTypes[fs] = $0; next}'
	HEADERIZE='/^Filesystem/ {print header; next}'
	FORMAT='{size=$2; used=$3; avail=$4; usePct=$5; mountedOn=$9; for(i=10; i<=NF; i++) mountedOn = mountedOn " " $i; $2=fsTypes[$1]; $3=size; $4=used; $5=avail; $6=usePct; $7=mountedOn}'
	NORMALIZE='{sub("^/dev/", "", $1); sub("s[0-9]+$", "", $1)}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	assertHaveCommand mount
	assertHaveCommand df
	CMD='eval mount -t nodevfs,nonfs,noswap,nocd9660; df -h -t nodevfs,nonfs,noswap,nocd9660'
	MAP_FS_TO_TYPE='/ on / {fs=$1; sub("^.*\134(", "", $0); sub(",.*$", "", $0); fsTypes[fs] = $0; next}'
	HEADERIZE='/^Filesystem/ {print header; next}'
	FORMAT='{size=$2; used=$3; avail=$4; usePct=$5; mountedOn=$6; $2=fsTypes[$1]; $3=size; $4=used; $5=avail; $6=usePct; $7=mountedOn}'
fi

$CMD | tee $TEE_DEST | $AWK "$BEGIN $HEADERIZE $FILTER_PRE $MAP_FS_TO_TYPE $FORMAT $FILTER_POST $NORMALIZE $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$BEGIN $HEADERIZE $FILTER_PRE $MAP_FS_TO_TYPE $FORMAT $FILTER_POST $NORMALIZE $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
