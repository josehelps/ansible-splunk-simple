'''
Copyright (C) 2005-2012 Splunk Inc. All Rights Reserved.
'''
import argparse
import csv
import logging
import os
import sys
import textwrap

import splunk
import splunk.Intersplunk


class IntegerRange(object):
    '''Class for use as an argument type in an ArgumentParser.
    The __call__ function will validate whether the string passed as the
    argument is a valid integer range.
    '''

    def __init__(self):
        self._ERRSTR = "Invalid input: argument must be a hyphen-separated range of integers in the form <low>-<high>."
    
    def __call__(self, val):
        '''Returns a tuple of integers (low, high) derived from the input string.
        If the input string is not a valid range of integers, raises ArgumentTypeError.
        '''
        try:
            low, high = map(int, val.split('-'))
            if low < high:
                return (low, high)
            else:
                raise argparse.ArgumentTypeError(self._ERRSTR)
        except Exception:
            raise argparse.ArgumentTypeError(self._ERRSTR)


def getopts(argv=None):

    desc = '''
    Script for mapping nCircle fine-grained severities to coarse severities
    for use in the Splunk App for Enterprise Security.
            
    This script can be run from the command-line or as a Splunk
    search command.
        
    Example of interactive use via the Splunk search bar:
    
        | ncircleseverities -I 0-10 -L 11-20 -M 21-30 -H 31-40 -C 41-53
        
    Example of interactive use via the command line:
    
        $SPLUNK_HOME/bin/splunk cmd python  $SPLUNK_HOME/etc/apps/TA-ncircle/bin/generate_ncircle_severities.py -I 0-10 -L 11-20 -M 21-30 -H 31-40 -C 41-50 -t /tmp/tmp.csv
    
    Execution occurs one of two ways:
    
    1) When run as a Splunk search command, no TTY should be present. The
       lookup table <current_app>/lookups/ncircle_severities.csv will
       be rewritten with the new severity specifications. The output
       file can not be overridden in this scenario, to prevent malicious
       access to the filesystem.
            
    2) If a TTY is present, the script assumes that it is being executed via
       the CLI. A target file can be specified via the "-t" switch. 
       Interactive execution can be used to output the generated lookup table
       to a separate CSV for inspection.    
    '''

    parser = argparse.ArgumentParser(description=textwrap.dedent(desc),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-t',
        dest='target_filename',
        type=str,
        action='store',
        help='Path to the target lookup file.',
        default=None)

    help_text = 'Integer range for "%s" severity events.'

    parser.add_argument('-I', '--info',
        dest='information',
        type=IntegerRange(),
        action='store',
        required=True,
        help=help_text % 'information',
        default="0-50")

    parser.add_argument('-L', '--low',
        dest='low',
        type=IntegerRange(),
        action='store',
        required=True,
        help=help_text % 'low',
        default="51-100")

    parser.add_argument('-M', '--medium',
        dest='medium',
        type=IntegerRange(),
        action='store',
        required=True,
        help=help_text % 'medium',
        default="101-150")

    parser.add_argument('-H', '--high',
        dest='high',
        type=IntegerRange(),
        action='store',
        required=True,
        help=help_text % 'high',
        default="151-200")

    parser.add_argument('-C', '--crit',
        dest='critical',
        type=IntegerRange(),
        action='store',
        required=True,
        help=help_text % 'critical',
        default="201-1000")

    return(parser.parse_args(argv))


def gen_csv(options):
    
    fields = ['severity_id', 'severity']
    # Use a list of severities so that the output is ordered, for convenience.
    severities = ['information', 'low', 'medium', 'high', 'critical']
    target_filename = options.get('target_filename', None)
    rows = []
    errors = []
    
    try:
        with open(target_filename, 'w') as f:
            writer = csv.DictWriter(f, fields)
            writer.writeheader()
            for severity in severities:
                low, high = options.get(severity)
                for i in xrange(low, high + 1):
                    rows.append(dict(zip(fields, [i, severity])))
    
            writer.writerows(rows)
    except IOError as e:
        errors.append("IOError on file %s: %s" % (target_filename, e.strerror))
    except Exception as e:
        errors.append("Unknown exception: %s" % e.strerror)

    return (rows, errors)

if __name__ == '__main__':

    # Retrieve the options for this script execution.
    options = getopts(sys.argv[1:])
    
    # Set umask.
    os.umask(022)

    # Set the default target file.
    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_target_file = os.path.join(parent, 'lookups', 'ncircle_severities.csv')

    if not sys.stdin.isatty():
        # Running as Splunk search command.
        # 1. Write only to the predefined lookup table location.
        # 2. Log messages go to STDERR where they will become search banner messages.
        # 3. Messages must be prefixed with WARN level or higher
        #    to be displayed.
        output = sys.stderr
        output_prefix_info = 'WARN'
        output_prefix_err = "ERROR"

        if options.target_filename:
            raise ValueError("Target filename cannot be specified when this script is run as a Splunk search command.")
        else:
            setattr(options, 'target_filename', default_target_file)
    else:
        # Running interactively.
        # 1. Writing to anywhere on the filesystem is permitted.
        # 2. Correct for misleading output prefixes.
        output = sys.stdout
        output_prefix_info = ""
        output_prefix_err = ""
        if not options.target_filename:
            setattr(options, 'target_filename', default_target_file)
    
    rows, errors = gen_csv(options.__dict__)

    if not errors:
        output.write("%s SUCCESS: Created lookup table mapping nCircle severities to Splunk severities (%d rows).\n" % (output_prefix_info, len(rows)))
        output.write("%s          target_file: %s\n" % (output_prefix_info, options.target_filename))
    else:
        output.write("%s FAILURE: Error creating lookup table.\n" % output_prefix_err)
        for errstr in errors:
            output.write("%s FAILURE DETAILS %s\n" % (output_prefix_err, errstr))

    splunk.Intersplunk.outputResults(rows)
