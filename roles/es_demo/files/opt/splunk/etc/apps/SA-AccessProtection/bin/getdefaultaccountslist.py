'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import csv
import httplib2
import re
import os
import sys
import urllib

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760) 


passwords_list_url = 'http://www.cirt.net/passwords'
app = 'SA-AccessProtection'
file = 'default_user_accounts.csv'
max_accounts = 100000

## Override Defaults w/ opts below
if len(sys.argv) > 1:
    for a in sys.argv:
        if a.startswith('app='):
            where = a.find('=')
            app = a[where+1:len(a)]
        elif a.startswith('file='):
            where = a.find('=')
            file = a[where+1:len(a)]
        elif a.startswith('max_accounts='):
            where = a.find('=')
            max_accounts = a[where+1:len(a)]
            
            
def get_list( verbose = True ):
    
    # 1 -- Get the list of accounts in HTML format
    resp, content = httplib2.Http().request(passwords_list_url, 'GET')
    
    # Find all entries
    users = []
    c = 0
    
    # 2 -- Iterate through each entry and add it to the list
    for match in re.finditer('href[=]["][?]vendor[=]([-a-zA-Z0-9 ().,&]+)["]', content):
        
        # 2.1 -- Parse out the URL components
        vendor_url = match.group(0)
        vendor = match.group(1)
        
        if verbose:
            print 'Downloading entry for', vendor
        
        # 2.2 -- Parse the information from the entry
        params = urllib.urlencode({'vendor': vendor})
        vendor_password_url = passwords_list_url + ("?%s" % params)
        resp, content = httplib2.Http().request(vendor_password_url,'GET')
        
        # 2.3 -- Get each of the attributes necessary
        for table in re.finditer('<table[ a-zA-Z0-9%=]*>(.*?)</table>', content, re.MULTILINE | re.DOTALL):
            
            # 2.3.1 -- Create the dictionary that will be populated
            user = {} 
            
            # 2.3.2 -- Create the regular expressions to populate the list
            user_re = '<b>User ID</b></td><td[ a-zA-Z0-9%=]*>(.*?)</td>'
            password_re = '<b>Password&nbsp;</b></td><td[ a-zA-Z0-9%=]*>(.*)</td>'
            level_re = '<b>Level</b></td><td[ a-zA-Z0-9%=]*>(.*)</td>'
            
            # 2.3.3 -- Get the user name
            user_match = re.search(user_re, table.group(1), re.MULTILINE)
            
            if user_match is not None:
                user['user'] = user_match.group(1)
                
            # 2.3.4 -- Get the the password
            password_match = re.search(password_re, table.group(1), re.MULTILINE)
            
            if password_match is not None:
                user['password'] = password_match.group(1)
                
            # 2.3.5 -- Get the the level
            level_match = re.search(level_re, table.group(1), re.MULTILINE)
            
            if level_match is not None and level_match.group(1).lower() in ['admin', 'administrator', 'root', 'administrative', 'administration', 'system administrator' ]:
                user['is_privileged'] = "true"
            else:
                user['is_privileged'] = "false"
                
            # 2.3.6 -- Populate the vendor field
            user['vendor'] = vendor
            
            if user.has_key('user'): 
                users.append(user)
            
        c = c + 1
        
        if c > max_accounts:
            return users
        
    return users
    
def output_to_accounts_csv( accounts, app, csv_file ):
    
    # 1 -- Get the full file path and open the file
    grandparent = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) 
    # go from app dir to lookups dir to lookup file 
    file = os.path.join(grandparent, app, 'lookups', csv_file)
    
    outFile = open(file,'w')
    
    # 2 -- Write out the CSV header
    header = ['user','is_privileged','is_default', 'is_watchlist']
    csv.writer(outFile, lineterminator='\n').writerow(header)
    
    # 3 -- Open the CSV file
    outputCSV = csv.DictWriter(outFile, header, lineterminator='\n')
    
    # 4 -- Write out each entry
    for account in accounts:
        
        if account['user'].lower() != '(none)':
            acct = {}
            acct['user'] = account['user']
            acct['is_privileged'] = account['is_privileged']
            
            acct['is_default'] = 'true'
            acct['is_watchlist'] = ''
            
            outputCSV.writerow(acct)
    
    
def update_default_account_list(app, file):
    
    # Get the accounts
    accounts = get_list()
    
    # Output the accounts to the CSV file
    output_to_accounts_csv(accounts, app, file)
    
update_default_account_list(app, file)