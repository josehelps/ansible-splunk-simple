#!/bin/sh
# Copyright 2011 Splunk, Inc.
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
#
# credit for improvement to http://splunk-base.splunk.com/answers/41391/rlogsh-using-too-much-cpu
. `dirname $0`/common.sh

SEEK_FILE=$SPLUNK_HOME/var/run/splunk/unix_audit_seekfile
AUDIT_FILE=/var/log/audit/audit.log

if [ "x$KERNEL" = "xLinux" ] ; then
    assertInvokerIsSuperuser
    assertHaveCommand service
    assertHaveCommandGivenPath /sbin/ausearch
    if [ -n "`service auditd status`" -a "$?" -eq 0 ] ; then
            if [ -a $SEEK_FILE ] ; then
                SEEK=`head -1 $SEEK_FILE`
            else
                SEEK=1
                echo "0" > $SEEK_FILE
            fi
            FILE_LINES=`wc -l $AUDIT_FILE  | cut -d " " -f 1`
            if [ $FILE_LINES -lt $SEEK ] ; then
                # audit file has wrapped
                SEEK=0
            fi
            awk -v START=$SEEK -v OUTPUT=$SEEK_FILE 'NR>START { print } END { print NR > OUTPUT }' $AUDIT_FILE | tee $TEE_DEST | /sbin/ausearch -i 2>/dev/null | grep -v "^----"
    fi
elif [ "x$KERNEL" = "xSunOS" ] ; then
    :
elif [ "x$KERNEL" = "xDarwin" ] ; then
    :
elif [ "x$KERNEL" = "xHP-UX" ] ; then
	:
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	:
fi
