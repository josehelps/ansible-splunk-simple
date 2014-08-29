'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import os
import subprocess
import sys

args = []
args.append('')
python_home = '/usr/bin/python'
ecmd_app = ''
ecmd_file = ''

## Override Defaults w/ opts below
if len(sys.argv) > 1:
	for a in sys.argv:
		args.append(a)
		if a.startswith('python_home='):
			where = a.find('=')
			python_home = a[where+1:len(a)]
		if a.startswith('ecmd_app='):
			where = a.find('=')
			ecmd_app = a[where+1:len(a)]
		elif a.startswith('ecmd_file='):
			where = a.find('=')
			ecmd_file = a[where+1:len(a)]

else:
	args.append('')
	
args[0] = python_home

# 1 -- Get the full file path and open the file
grandparent = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) 
args[1] = os.path.join(grandparent, ecmd_app, 'bin', ecmd_file)
args = ' '.join(args)
args = args.strip()

extScript = subprocess.Popen(args, shell=True, stdin=sys.stdin, stderr=sys.stderr, stdout=sys.stdout)

## close process	
extScript.communicate()