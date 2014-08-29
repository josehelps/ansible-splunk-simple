import smtplib, sys, StringIO, base64, os, socket, urllib, urllib2, urlparse, ssl
import splunk.admin as admin
import splunk.entity as en
import splunk.rest as rest
import splunk.util
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.header import Header


charset = "UTF-8"
def isASCII(str):
    for i in str:
        if ord(i) > 127:
            return False
    return True

def toBool(strVal):
   if strVal == None:
       return False

   lStrVal = strVal.lower()
   if lStrVal == "true" or lStrVal == "t" or lStrVal == "1" or lStrVal == "yes" or lStrVal == "y" :
       return True 
   return False


class SendemailRestHandler(admin.MConfigHandler):

  def __init__(self, scriptMode, ctxInfo):
      admin.MConfigHandler.__init__(self, scriptMode, ctxInfo)
      self.shouldAutoList = False

  # get firs arg
  def gfa(self, name, defaultVal=''):
      if self.hasNonEmptyArg(name):
         val = self.callerArgs.get(name, [defaultVal])[0]
         if val != None: return val
      return defaultVal

  def hasNonEmptyArg(self, name):
      return name in self.callerArgs and self.callerArgs.get(name) != None

  def setup(self):
    if self.requestedAction == admin.ACTION_CREATE or self.requestedAction == admin.ACTION_EDIT:
      for arg in ['to', 'body']:
          self.supportedArgs.addReqArg(arg)
       
      for arg in ['cc', 'bcc', 'from', 'subject', 'format', 'username', 'password', 'server', 'use_ssl', 'use_tls']:
          self.supportedArgs.addOptArg(arg)

  def handleList(self, confInfo):
      pass 
  
  def handleCreate(self, confInfo):
    message = MIMEMultipart()
  
    subject    = self.gfa('subject')
    body       = self.gfa('body')
    bodyformat = self.gfa('format', 'html')

    mailserver = self.gfa('server', 'localhost')
    username   = self.gfa('username')
    password   = self.gfa('password')
 
    use_ssl    = toBool(self.gfa('use_ssl'))
    use_tls    = toBool(self.gfa('use_tls'))

    if isASCII(subject):
        message['Subject'] = subject
    else:
        message['Subject'] = Header(subject, charset)

    recipients = []
    for t in self.callerArgs.get('to'):
        recipients.append(t.strip())
    message['To'] = ', '.join(self.callerArgs.get('to'))

    if self.hasNonEmptyArg('cc') :
       cc = [x for x in self.callerArgs.get('cc') if x != None]
       if len(cc) > 0:
           message['Cc'] = ', '.join(cc)
           for t in cc:
               recipients.append(t.strip())   

    if self.hasNonEmptyArg('bcc'):
       bcc = [x for x in self.callerArgs.get('bcc') if x != None]
       if len(bcc) > 0:
          message['Bcc'] = ', '.join(bcc)
          for t in bcc:
              recipients.append(t.strip())   

    sender = 'splunk'
    if self.hasNonEmptyArg('from'):
       sender = self.gfa('from')

    if sender.find("@") == -1:
       sender = sender + '@' + socket.gethostname()
       if sender.endswith("@"):
          sender = sender + 'localhost'

    message['From'] = sender

    message.attach(MIMEText(body, bodyformat, _charset=charset))


    # send the mail
    if not use_ssl:
         smtp = smtplib.SMTP(mailserver)
    else:
         smtp = smtplib.SMTP_SSL(mailserver)

    if use_tls:
         smtp.starttls()

    if len(username) > 0:
        smtp.login(username, password)

    smtp.sendmail(sender, recipients, message.as_string())
    smtp.quit()

# initialize the handler
admin.init(SendemailRestHandler, admin.CONTEXT_APP_AND_USER)

