##############
# log_fixer v 0.1
# 7/9/14
# Splunk, Inc.
##############
# Use this script to replace IP's and user names in sep events 
# The ip's and user names are in the dict user_ip
# The 'log' file has a singular sep transaction
# For each event in the transaction:
## we substiture orig_user with a user from the list
## we substitute an orig_ip with the user's matching ip 
# Opening and closing the same file is not the most efficient but
## it gives us a built in counter to get the next user_ip pair

log = '/Users/mmerza/Box Sync/es_demo/log/WinEventLog_Application_TrendMicro.txt'
orig_ip = "10.11.36.20"
orig_user = "User=Bill_williams"
orig_machine_name = "ComputerName=Bill_williams"
orig_file_location = "c:/Users/Bill_williams"
orig_system = "Kratos"

user_ip = {"10.11.36.31":"brian",
"10.11.36.32":"jose",
"10.11.36.33":"david",
"10.11.36.34":"joe",
"10.11.36.35":"seemi",
"10.11.36.36":"fred",
"10.11.36.37":"randy",
"10.11.36.38":"elly",
"10.11.36.39":"ben",
"10.11.36.40":"cindy",
"110.172.158.1":"todd",
"110.172.158.2":"vijay",
"110.172.158.3":"ice",
"110.172.158.4":"ed",
"110.172.158.5":"ed",
"110.172.158.6":"jack",
"110.172.158.7":"james",
"110.172.158.8":"dimitri",
"110.172.158.9":"bill",
"110.172.158.10":"jeff",
"110.172.158.11":"krish",
"110.172.158.12":"robert",
"110.172.158.13":"tom",
"110.172.158.14":"mod",
"110.172.158.15":"buttercup"}


for key in user_ip.keys():
    # open a file
    input_log = open(log, 'r')    
    #read a line
    for line in input_log:
        #reset the line_counter        
        line_counter = 0
        # replace the IP with the current IP
        #line = line.replace(orig_ip,key )
        # replace the machine name
        line = line.replace(orig_machine_name, ("ComputerName="+user_ip[key]+"-pc"))
        # replace user name
        line = line.replace(orig_user, "User="+user_ip[key])
        #replace file location
        line = line.replace(orig_file_location, "c:/Users/"+user_ip[key])
        line = line.replace(orig_system, key)
        print line,
    #close the file
    input_log.close()