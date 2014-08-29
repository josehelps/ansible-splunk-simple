#   Version 4.0
#!/usr/bin/env python


# nmap -p 80,8000,8080,8088 tiny.splunk.com
# nmap -sP -T insane -oG foo mcdavid/24
# 
# grepable =  -oG
# OS = -O
# 
# sudo nmap  tiny
# sudo nmap -O tiny/24
# sudo nmap -sX -O tiny
# nmap -v -O tiny
#

import os, time, stat, re, sys, subprocess
import crawl
import logging as logger

NETWORKCMD = "nmap %s/%s"

# !! need to ensure no quotes, spaces, ;, etc.  no funny business in command.
def exeCommand(command, input = ""):
     logger.info("network crawl = %s" % command)
     p = subprocess.Popen(command.split(' '),stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
     output = p.communicate(input + "\n")[0]
     return output
 
class NetworkCrawler(crawl.Crawler):

    def __init__(self, mgr, args):
         name = args.get("name", "network")
         crawl.Crawler.__init__(self, name, mgr, args)
         self.network_info = {}
         # GET SETTINGS
         logger.info("network crawl settings =  '%s'" % self.settings)
         self.index  = self.getSetting("index", "main")
         self.host   = self.getSetting("host", "localhost")         
         self.subnet = self.getSetting("subnet", "64")         
     
    def execute(self):
        # CRAWL
        events = self._doCrawl()
        
        # CREATE RESULT ACTIONS
        actions = []
        for event in events:
             event['_time'] = time.time()
             event['crawler_type'] = self.name
             event['index'] = self.index
             actions.append(crawl.AddHostAction(event))
        return actions

    def _doCrawl(self):
         lines = (exeCommand( NETWORKCMD % (self.host, self.subnet) )).split('\n')
         events = []
         for line in lines:
              match = re.match("^(?P<_raw>(?P<portnum>\d+)/(?P<type>\S+)\s+(?P<state>\S+)\s+(?P<service>\S+))$", line)
              if match:
                   events.append(match.groupdict())
         return events
