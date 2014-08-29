#   Version 4.0
import os
import re
import sys
import urllib
import splunk.Intersplunk
import splunk.mining.dcutils as dcu
import subprocess
from subprocess import PIPE, STDOUT

logger    = dcu.getLogger()
mswindows = (sys.platform == "win32")

results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

# These values will be sent to the shell script:
# $0 = scriptname
# $1 = number of events returned
# $2 = search terms
# $3 = fully qualified query string
# $4 = name of saved splunk
# $5 = trigger reason (i.e. "The number of events was greater than 1")
# $6 = link to saved search
# $7 = DEPRECATED - empty string argument
# $8 = file where the results for this search are stored(contains raw results)

# 5 corresponds to the 6th arg passed to this python script which includes the
# name of this script and the path where the user's script is located

# The script will also receive args via stdin - currently only the session
# key which it can use to communicate back to splunkd is sent via stdin. 
# The format for stdin args is as follows:
# <url-encoded-name>=<url-encoded-value>\n
# e.g.
# sessionKey=0729f8e0d4edf7ae18327da6a9976596
# otherArg=123456
# <eof> 


if len(sys.argv) < 10:
    splunk.Intersplunk.generateErrorResults("Missing arguments to operator 'runshellscript', expected at least 10, got %i." % len(sys.argv))
    exit(1)

script   = sys.argv[1]

if not script:
    splunk.Intersplunk.generateErrorResults("Empty string is not a valid script name")
    exit(2)
    
# Remove possible enclosing single quotes
if script[0] == "'" and script[-1] == "'":
    script = script[1:-1]

sharedStorage = settings.get('sharedStorage', splunk.Intersplunk.splunkHome())

if len(sys.argv) > 10:
   path = sys.argv[10]   # the tenth arg is going to be the file 
else:
   baseStorage   = os.path.join(sharedStorage, 'var', 'run', 'splunk')
   path          = os.path.join(baseStorage, 'dispatch', sys.argv[9], 'results.csv.gz')


# ensure nothing dangerous
# keep this rule in agreement with etc/system/default/restmap.conf for sane UI
# experience in manager when editing alerts (SPL-49225)
if ".." in script or "/" in script or "\\" in script:
    results = splunk.Intersplunk.generateErrorResults('Script location cannot contain "..", "/", or "\\"')
else:
    
    # look for scripts first in the app's bin/scripts/ dir, if that fails try SPLUNK_HOME/bin/scripts
    namespace  = settings.get("namespace", None)
    sessionKey = settings.get("sessionKey", None)
    scriptName = script

    if namespace:
        script = os.path.join(sharedStorage,"etc","slave-apps",namespace,"bin","scripts",scriptName)
        if not os.path.exists(script):
            script = os.path.join(sharedStorage,"etc","apps",namespace,"bin","scripts",scriptName)

    # if we fail to find script in SPLUNK_HOME/etc/apps/<app>/bin/scripts - look in SPLUNK_HOME/bin/scripts
    if not namespace or not os.path.exists(script):
        script = os.path.join(splunk.Intersplunk.splunkHome(),"bin","scripts",scriptName)
        
    if not os.path.exists(script):
        results = splunk.Intersplunk.generateErrorResults('Cannot find script at ' + script)
    else:
        stdin_data = ''
        cmd_args = sys.argv[1:] # drop 'runshellscript'

        # make sure cmd_args has length of 9
        cmd_args    = cmd_args[:9]
        for i in range(9-len(cmd_args)):
           cmd_args.append("")
        cmd_args[0] = script
        cmd_args[8] = path

        stdin_data = "sessionKey=" + urllib.quote(sessionKey) + "\n"

        # strip any single/double quoting         
        for i in xrange(len(cmd_args)):
            if len(cmd_args[i]) > 2 and ((cmd_args[i][0] == '"' and cmd_args[i][-1] == '"') or (cmd_args[i][0] == "'" and cmd_args[i][-1] == "'")):
                 cmd_args[i] = cmd_args[i][1:-1]	

        # python's call(..., shell=True,...)  - is broken so we emulate it ourselves
        shell_cmd   = ["/bin/sh"]
        cmd_args_ms = []

        # by default using cmd.exe shell
        use_cmd_exe = True
        if mswindows:
            # escape all special characters of cmd.exe
            cmd_args_ms = []

            # do not escape the first argument, since this is a script name which was validated above for existence
            cmd_args_ms.append(cmd_args[0])
            for i in range(1, len(cmd_args)):

                # 1. cmd.exe uses the following characters for escaping other characters: \,%,^. Escape them with themselves, e.g. %->%%, ^->^^, \->\\
                temp = re.sub('([\\\%\^])','\\1\\1', cmd_args[i])

                # 2. cmd.exe escapes set &><|'`,;=() using ^, set of []" with \ and escapes ! with ^^. 
                temp = re.sub('([\&\>\<\|\'\`\,\;\=\(\)])','^\\1', temp) # &><|'`,;=()
                temp = re.sub('([\[\]\"])','\\\\\\1', temp) # []"
                temp = re.sub('([\!])','^^\\1', temp) # !
                cmd_args_ms.append(temp)

            logger.info(str(cmd_args_ms))
        else:
            logger.info(str(cmd_args))


        # try to read the interpreter from the first line of the file
        try:
            f = open(script)
            line = f.readline().rstrip("\r\n")
            f.close()
            if line.startswith("#!"):
                use_cmd_exe = False

                # Emulate UNIX rules for "#!" lines:
                # 1. Any whitespace (just space and tab, actually) after
                #    the "!" is ignored.  Also whitespace at the end of
                #    the line is dropped
                # 2. Anything up to the next whitespace is the interpreter
                # 3. If there is anything after this whitespace it's
                #    considered to be the argument to pass to the interpreter.
                #    Note that this parsing is very simple -- no quoting
                #    is interpreted and only one argument is parsed.  This
                #    is to match
                line = line[2:].strip(" \t")
                if line:
                    arg_loc = line.replace("\t", " ").find(" ")
                    if arg_loc == -1:
                        shell_cmd = [ line ]
                    else:
                        # The second half here is incorrect; and will break if
                        # the #! includes more than one arg, on unix,
                        # line.split() would be correct
                        shell_cmd = [ line[0:arg_loc], line[arg_loc + 1:].lstrip(" \t") ]
            elif script.endswith(".py"):
                # Try to support python scripts in a portable way.
                # Note, if the user specified a #!, then that takes precedence
                # (eg, run with system python)
                use_cmd_exe = False # python won't understand the escaped stuff

                if mswindows:
                    python_exe = "python.exe"
                else:
                    python_exe = "python"
                python_path = os.path.join(sharedStorage, "bin", python_exe)
                shell_cmd = [ python_path ]

        except Exception, e:
            pass

        # pass args as env variables too - this is to ensure that args are properly passed in windows
        for i in range(len(cmd_args)):
            os.environ['SPLUNK_ARG_' + str(i)] = cmd_args[i]

        try:
            p = None
            if mswindows and use_cmd_exe:
                cmd2run = cmd_args_ms
                logger.info("runshellscript: " + str(cmd2run))

                p = subprocess.Popen(cmd2run, stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=False)
            else:     
                logger.info("runshellscript: " + str(shell_cmd + cmd_args))
                if mswindows:  # windows doesn't support close_fds param
                    p = subprocess.Popen(shell_cmd + cmd_args, stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=False)
                else:
                    p = subprocess.Popen(shell_cmd + cmd_args, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True, shell=False)

            if p: 
               p.communicate(input=stdin_data)
        except OSError, e:
            results = splunk.Intersplunk.generateErrorResults('Error while executing script ' + str(e))
splunk.Intersplunk.outputResults( results )
