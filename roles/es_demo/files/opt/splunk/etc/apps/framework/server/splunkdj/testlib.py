# 
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Helper functions for wrinting unit tests for apps built using the
   Splunk Django Bindings."""

from os import path
import sys

__all__ = ["loadrc"]

# Print the given message to stderr, and optionally exit
def error(message, exitcode = None):
    print >> sys.stderr, "Error: %s" % message
    if not exitcode is None: sys.exit(exitcode)

def loadrc(filepath):
    """Load a `.splunkrc` style options file and return a `dict` of option 
       values."""
    filepath = path.expanduser(filepath) # Just in case

    argv = []
    try:
        file = open(filepath)
    except:
        error("Unable to open '%s'" % filepath, 2)

    result = {}
    for line in file:
        if line.startswith("#"): continue # Skip comment
        line = line.strip()
        if len(line) == 0: continue # Skip blank line
        k, v = line.split('=', 1)
        result[k] = v

    return result
