import re, time, splunk.Intersplunk, splunk.mining.dcutils as dcu
import smtplib, socket, urllib, urllib2, urlparse, ssl
import json
from mako import template 
import mako.filters as filters
import copy

import cStringIO, csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.header import Header

import splunk.search as search
import splunk.entity as entity
from splunk.util import setSSLWrapProtocol
from splunk.util import normalizeBoolean 
from splunk.rest import simpleRequest
from splunk.saved import savedSearchJSONIsAlert

PDF_REPORT_SERVER_TIMEOUT = 600
PDFGEN_SIMPLE_REQUEST_TIMEOUT = 3600
EMAIL_DELIM = re.compile('\s*[,;]\s*')
CHARSET = "UTF-8"
IMPORTANCE_MAP = {
    "highest": "1 (Highest)",
    "high"   : "2 (High)",
    "low"    : "4 (Low)",
    "lowest" : "5 (Lowest)",
    "1" : "1 (Highest)",
    "2" : "2 (High)",
    "4" : "4 (Low)",
    "5" : "5 (Lowest)"
}

logger = dcu.getLogger()

class PDFException(Exception):
    pass

def unquote(val):
    if val is not None and len(val) > 1 and val.startswith('"') and val.endswith('"'):
       return val[1:-1]
    return val

def numsort(x, y):
    if y[1] > x[1]:
        return -1
    elif x[1] > y[1]:
        return 1
    else:
        return 0

def renderTime(results):
   for result in results:
      if "_time" in result:
         try:
              result["_time"] = time.ctime(float(result["_time"]))
         except: 
              pass

def mail(email, argvals, ssContent):

    sender     = email['From']
    use_ssl    = normalizeBoolean(ssContent.get('action.email.use_ssl', False))
    use_tls    = normalizeBoolean(ssContent.get('action.email.use_tls', False))        
    server     = ssContent.get('action.email.mailserver', 'localhost')
    username   = argvals.get('username', '')
    password   = argvals.get('password', '')
    recipients = []

    if email['To']:
        recipients.extend(EMAIL_DELIM.split(email['To']))
    if email['Cc']:
        recipients.extend(EMAIL_DELIM.split(email['Cc']))
    if email['Bcc']:
        recipients.extend(EMAIL_DELIM.split(email['Bcc']))

    # Clear leading / trailing whitespace from recipients
    recipients = [r.strip() for r in recipients]

    mail_log_msg = 'Sending email. subject="%s", results_link="%s", recipients="%s"' % (
        ssContent.get('action.email.subject'), 
        ssContent.get('results_link'), 
        str(recipients)
    ) 
    try:
        # make sure the sender is a valid email address
        if sender.find("@") == -1:
            sender = sender + '@' + socket.gethostname()
            if sender.endswith("@"):
              sender = sender + 'localhost'

        # send the mail
        if not use_ssl:
            smtp = smtplib.SMTP(server)
        else:
            smtp = smtplib.SMTP_SSL(server)

        if use_tls:
           smtp.starttls()
        if len(username) > 0 and len(password) >0:
           smtp.login(username, password)

        #logger.info('email = %s', email.as_string())
        smtp.sendmail(sender, recipients, email.as_string())
        smtp.quit()
        logger.info(mail_log_msg)

    except Exception, e:
        logger.error(mail_log_msg)
        raise

def sendEmail(results, settings):
    keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()

    for key in argvals:
        argvals[key] =  unquote(argvals[key])

    namespace       = settings['namespace']
    owner           = settings['owner']
    sessionKey      = settings['sessionKey']
    sid             = settings['sid']
    ssname          = argvals.get('ssname')
    isScheduledView = False

    if ssname: 
        # populate content with savedsearch
        if '_ScheduledView__' in ssname or argvals.get('pdfview'):
            if '_ScheduledView__' in ssname:
                ssname = ssname.replace('_ScheduledView__', '')
            else:
                ssname = argvals.get('pdfview')

            uri = entity.buildEndpoint(
                [ 'scheduled', 'views', ssname], 
                namespace=namespace, 
                owner=owner
            )
            isScheduledView = True

        else: 
            uri = entity.buildEndpoint(
                [
                    'saved', 
                    'searches', 
                    ssname
                ], 
                namespace=namespace, 
                owner=owner
            )

        responseHeaders, responseBody = simpleRequest(uri, method='GET', getargs={'output_mode':'json'}, sessionKey=sessionKey)

        savedSearch = json.loads(responseBody)
        ssContent = savedSearch['entry'][0]['content']

        # set type of saved search
        if isScheduledView: 
            ssContent['type']  = 'view'
        elif savedSearchJSONIsAlert(savedSearch):
            ssContent['type']  = 'alert'
        else:
            ssContent['type']  = 'report'

        # remap needed attributes that are not already on the content
        ssContent['name']                 = ssname
        ssContent['app']                  = savedSearch['entry'][0]['acl'].get('app')
        ssContent['owner']                = savedSearch['entry'][0]['acl'].get('owner')

        # The footer.text key will always exist for type alert and report. 
        # It may not exist for scheduled views created before 6.1 therefore the schedule view default footer.text 
        # should be set if the key does not exist.
        # This can be removed once migration has happened to ensure scheduled views always have the footer.text attribute
        ssContent['action.email.footer.text'] = ssContent.get('action.email.footer.text', "If you believe you've received this email in error, please see your Splunk administrator.\r\n\r\nsplunk > the engine for machine data")

        # The message key will always exist for type alert and report. 
        # It may not exist for scheduled views created before 6.1 therefore the schedule view default message 
        # should be set if the key does not exist.
        # This can be removed once migration has happened to ensure scheduled views always have the message.view attribute
        ssContent['action.email.message'] = ssContent.get('action.email.message.' + ssContent.get('type'), 'A PDF was generated for $name$')
        if normalizeBoolean(ssContent.get('action.email.useNSSubject', False)):
            ssContent['action.email.subject'] = ssContent['action.email.subject.' + ssContent.get('type')]

        # prior to 6.1 the results link was sent as the argval sslink, must check both results_link
        # and sslink for backwards compatibility
        ssContent['results_link'] = argvals.get('results_link', argvals.get('sslink', ''))
        if normalizeBoolean(ssContent['results_link']) and normalizeBoolean(ssContent['type']):
            split_results_path = urllib.splitquery(ssContent.get('results_link'))[0].split('/')
            view_path = '/'.join(split_results_path[:-1]) + '/'
            ssType = ssContent.get('type')
            if ssType == 'alert':
                ssContent['view_link'] = view_path + 'alert?' + urllib.urlencode({'s': savedSearch['entry'][0]['links'].get('alternate')})
            elif ssType == 'report':
                ssContent['view_link'] = view_path + 'report?' + urllib.urlencode({'s': savedSearch['entry'][0]['links'].get('alternate'), 'sid': sid})
            elif ssType == 'view':
                ssContent['view_link'] = view_path + ssContent['name']
            else:
                ssContent['view_link'] = view_path + 'search'
    else:
        #assumes that if no ssname then called from searchbar
        ssContent = {
            'type': 'searchCommand',
            'view_link': '',
            'action.email.sendresults': False,
            'action.email.sendpdf': False,
            'action.email.sendcsv': False,
            'action.email.inline': True,
            'action.email.format': 'table',
            'action.email.subject': 'Splunk Results',
            'action.email.footer.text': "If you believe you've received this email in error, please see your Splunk administrator.\r\n\r\nsplunk > the engine for machine data"
        }

    ssContent['trigger_date'] = None
    ssContent['trigger_timeHMS'] = None
    ssContent['trigger_time'] = argvals.get('trigger_time')
    ssContent
    if normalizeBoolean(ssContent['trigger_time']):
        try:
            triggerSeconds = time.localtime(float(ssContent['trigger_time']))
            ssContent['trigger_date'] = time.strftime("%B %d, %Y", triggerSeconds)
            ssContent['trigger_timeHMS'] = time.strftime("%I:%M:%S", triggerSeconds)
        except Exception, e:
            logger.info(e)

    # layer in arg vals
    if argvals.get('to'):
        ssContent['action.email.to'] = argvals.get('to')
    if argvals.get('bcc'):
        ssContent['action.email.bcc'] = argvals.get('bcc')
    if argvals.get('cc'):
        ssContent['action.email.cc'] = argvals.get('cc')
    if argvals.get('format'):
        ssContent['action.email.format'] = argvals.get('format')
    if argvals.get('from'):
        ssContent['action.email.from'] = argvals.get('from')
    if argvals.get('inline'):
        ssContent['action.email.inline'] = normalizeBoolean(argvals.get('inline'))
    if argvals.get('sendresults'):
        ssContent['action.email.sendresults'] = normalizeBoolean(argvals.get('sendresults'))
    if argvals.get('sendpdf'):
        ssContent['action.email.sendpdf'] = normalizeBoolean(argvals.get('sendpdf'))
    if argvals.get('pdfview'):
        ssContent['action.email.pdfview'] = argvals.get('pdfview')
    if argvals.get('papersize'):
        ssContent['action.email.reportPaperSize'] = argvals.get('papersize')
    if argvals.get('paperorientation'):
        ssContent['action.email.reportPaperOrientation'] = argvals.get('paperorientation')
    if argvals.get('sendcsv'):
        ssContent['action.email.sendcsv'] = normalizeBoolean(argvals.get('sendcsv'))
    if argvals.get('server'):
        ssContent['action.email.mailserver'] = argvals.get('server')
    if argvals.get('subject'):
        ssContent['action.email.subject'] = argvals.get('subject')
    if argvals.get('footer'):
        ssContent['action.email.footer.text'] = argvals.get('footer')
    if argvals.get('width_sort_columns'):
        ssContent['action.email.width_sort_columns'] = normalizeBoolean(argvals.get('width_sort_columns'))
    if argvals.get('message'):
        ssContent['action.email.message'] = argvals.get('message')
    else:
        if ssContent['type'] == 'searchCommand':
            # set default message for searchCommand emails
            if ssContent['action.email.sendresults'] or ssContent['action.email.sendpdf'] or ssContent['action.email.sendcsv']:
                if ssContent['action.email.inline'] and not(ssContent['action.email.sendpdf'] or ssContent['action.email.sendcsv']):
                    ssContent['action.email.message'] = 'Search results.'
                else:
                    ssContent['action.email.message'] = 'Search results attached.'
            else:
                ssContent['action.email.message'] = 'Search complete.'
    if argvals.get('priority'):
        ssContent['action.email.priority'] = argvals.get('priority')
    if argvals.get('use_ssl'):
        ssContent['action.email.use_ssl'] = normalizeBoolean(argvals.get('use_ssl'))
    if argvals.get('use_tls'):
        ssContent['action.email.use_tls'] = normalizeBoolean(argvals.get('use_tls'))
    
    ssContent['graceful'] = normalizeBoolean(argvals.get('graceful', 0))

    #if there is no results_link then do not incude it
    if not normalizeBoolean(ssContent.get('results_link')):
        ssContent['action.email.include.results_link'] = False

    #need for backwards compatibility 
    format = ssContent.get('action.email.format')
    if format == 'html' or format == 'plain' or format == 'text':
        ssContent['action.email.format'] = 'table'

    #fetch server info
    uriToServerInfo = entity.buildEndpoint(['server', 'info'])
    serverInfoHeaders, serverInfoBody = simpleRequest(uriToServerInfo, method='GET', getargs={'output_mode':'json'}, sessionKey=sessionKey)
    
    serverInfo        = json.loads(serverInfoBody)
    serverInfoContent = serverInfo['entry'][0]['content']

    #fetch job info
    jobResponseHeaders = {} 
    jobResponseBody = { 
        'entry': [
            {
                'content': {}
            }
        ]
    }
    if sid: 
        uriToJob = entity.buildEndpoint(
            [
                'search', 
                'jobs', 
                sid
            ], 
            namespace=namespace, 
            owner=owner
        )
        jobResponseHeaders, jobResponseBody = simpleRequest(uriToJob, method='GET', getargs={'output_mode':'json'}, sessionKey=sessionKey)
    
    searchJob         = json.loads(jobResponseBody)
    jobContent        = searchJob['entry'][0]['content']

    valuesForTemplate = buildSafeMergedValues(ssContent, results, serverInfoContent, jobContent, argvals.get('results_file'))
    realize(valuesForTemplate, ssContent, sessionKey, namespace, owner)
    #Creation of the email object that is to be populated in the build 
    #prefixed methods.
    emailMix = MIMEMultipart('mixed')
    emailAlt = MIMEMultipart('alternative')
    emailMix.attach(emailAlt)

    #make time user readable
    resultsWithRenderedTime = copy.deepcopy(results)
    renderTime(resultsWithRenderedTime)

    #potentially mutate argvals if username/password are empty
    setUserCrendentials(argvals, settings)

    #build all the different email components
    jobCount = getJobCount(jobContent)
    #attachments must be added before body so body can inlclude errors cause by attachments
    buildAttachments(settings, ssContent, resultsWithRenderedTime, emailMix, jobCount)
    buildPlainTextBody(ssContent, resultsWithRenderedTime, settings, emailAlt, jobCount)
    buildHTMLBody(ssContent, resultsWithRenderedTime, settings, emailAlt, jobCount)
    buildHeaders(argvals, ssContent, emailMix, sid, serverInfoContent)

    try:
        mail(emailMix, argvals, ssContent)
    except Exception, e:
        errorMessage = str(e) + ' while sending mail to: ' + ssContent.get("action.email.to")
        logger.error(errorMessage)
        results = dcu.getErrorResults(results, ssContent['graceful'], errorMessage)
    return results

def buildSafeMergedValues(ssContent, results, serverInfoContent, jobContent, results_file):
    mergedObject = {}
     #namespace the keys
    for key, value in jobContent.iteritems():
        mergedObject['token.job.'+key] = value
    mergedObject['token.search_id'] = jobContent.get('sid')

    for key, value in ssContent.iteritems():
        mergedObject['token.'+key] = value

    mergedObject['token.name'] = ssContent.get('name')
    mergedObject['token.app'] = ssContent.get('app')
    mergedObject['token.owner'] = ssContent.get('owner')

    for key, value in serverInfoContent.iteritems():
        mergedObject['token.server.'+key] = value

    if results: 
        r = results[0]
        for k in r:
            mergedObject['token.result.'+k] = r[k]
        mergedObject['token.results.count'] = len(results)
    mergedObject['token.results.url'] = ssContent.get('results_link')
    mergedObject['token.results.file'] = results_file

    return mergedObject


def realize(valuesForTemplate, ssContent, sessionKey, namespace, owner):
    stringsForPost = {}
    if ssContent.get('action.email.message'):
        stringsForPost['action.email.message'] = ssContent['action.email.message']

    if ssContent.get('action.email.cc'):
        stringsForPost['action.email.cc'] = ssContent['action.email.cc']

    if ssContent.get('action.email.bcc'):
        stringsForPost['action.email.bcc'] = ssContent['action.email.bcc']

    if ssContent.get('action.email.to'):
        stringsForPost['action.email.to'] = ssContent['action.email.to']

    if ssContent.get('action.email.subject'):
        stringsForPost['action.email.subject'] = ssContent['action.email.subject']

    if ssContent.get('action.email.footer.text'):
        stringsForPost['action.email.footer.text'] = ssContent['action.email.footer.text']
    
    realizeURI = entity.buildEndpoint([ 'template', 'realize' ])

    postargs = valuesForTemplate
    postargs['output_mode'] = 'json'
    postargs['conf.recurse'] = 0
    try:
        for key, value in stringsForPost.iteritems():
            postargs['name'] = value
            headers, body = simpleRequest(
                realizeURI, 
                method='POST', 
                postargs=postargs, 
                sessionKey=sessionKey
            )
            body = json.loads(body)
            ssContent[key] = body['entry'][0]['content']['eai:data']
    except Exception, e:
        logger.info(e)

def setUserCrendentials(argvals, settings):
    username    = argvals.get("username" , "")
    password    = argvals.get("password" , "")

    # fetch credentials from the endpoint if none are supplied or password is encrypted
    if (len(username) == 0 and len(password) == 0) or password.startswith('$1$') :
        namespace  = settings.get("namespace", None)
        sessionKey = settings['sessionKey']

        username, password = getCredentials(sessionKey, namespace)
         
        argvals['username'] = username
        argvals['password'] = password

def getJobCount(jobContent):
    if jobContent.get('statusBuckets') == 0 or (normalizeBoolean(jobContent.get('reportSearch')) and not re.match('sendemail', jobContent.get('reportSearch'))):
        return jobContent.get('resultCount')
    else:
        return jobContent.get('eventCount')

# takes header, html, text
def buildHeaders(argvals, ssContent, email, sid, serverInfoContent):

    sender  = ssContent.get("action.email.from", "splunk")
    to      = ssContent.get("action.email.to")
    cc      = ssContent.get("action.email.cc")
    bcc     = ssContent.get("action.email.bcc")
    subject = ssContent.get("action.email.subject")
    priority = ssContent.get("action.email.priority", '')

    # use the Header object to specify UTF-8 msg headers, such as subject, to, cc etc
    email['Subject'] = Header(subject, CHARSET)

    recipients = []
    if to:
        email['To'] = to
    if sender:
        email['From'] = sender
    if cc:
        email['Cc'] = cc
    if bcc:
        email['Bcc'] = bcc

    if priority:
        # look up better name
        val = IMPORTANCE_MAP.get(priority.lower(), '')
        # unknown value, use value user supplied
        if not val:
            val = priority
        email['X-Priority'] = val

    # trace info
    if ssContent.get('name'):
        email['X-Splunk-Name'] = ssContent.get('name')
    if ssContent.get('owner'):
        email['X-Splunk-Owner'] = ssContent.get('owner')
    if ssContent.get('app'):
        email['X-Splunk-App'] = ssContent.get('app')
    email['X-Splunk-SID'] = sid
    email['X-Splunk-ServerName'] = serverInfoContent.get('serverName')
    email['X-Splunk-Version'] = serverInfoContent.get('version')
    email['X-Splunk-Build'] = serverInfoContent.get('build')


def buildHTMLBody(ssContent, results, settings, email, jobCount):
    messageHTML  = re.sub(r'\r\n?|\n', '<br \>\r\n', htmlMessageTemplate().render(msg=ssContent.get('action.email.message')))
    resultsHTML = ''
    metaDataHTML = ''
    errorHTML = ''
    if ssContent['type'] == 'view':
        metaDataHTML = htmlMetaDataViewTemplate().render(
            view_link=ssContent.get('view_link')
        )
        errorHTML = htmlErrorTemplate().render(errors=ssContent.get('errorArray'))
    else:
        if ssContent['type'] != 'searchCommand':
            metaDataHTML = htmlMetaDataSSTemplate().render(
                jobcount=jobCount,
                results_link=ssContent.get('results_link'),
                include_results_link=normalizeBoolean(ssContent.get('action.email.include.results_link')),
                view_link=ssContent.get('view_link'),
                include_view_link=normalizeBoolean(ssContent.get('action.email.include.view_link')),
                name=ssContent.get('name'),
                include_search=normalizeBoolean(ssContent.get('action.email.include.search')),
                ssquery=ssContent.get('search'),
                alert_type=ssContent.get('alert_type'),
                include_trigger=normalizeBoolean(ssContent.get('action.email.include.trigger')),
                include_inline=normalizeBoolean(ssContent.get('action.email.inline')),
                include_trigger_time=normalizeBoolean(ssContent.get('action.email.include.trigger_time')),
                trigger_date=ssContent.get('trigger_date'),
                trigger_timeHMS=ssContent.get('trigger_timeHMS'),
                ssType=ssContent.get('type'),
            )
        errorHTML = htmlErrorTemplate().render(errors=ssContent.get('errorArray'))
        # need to check aciton.email.sendresults for type searchCommand
        if normalizeBoolean(ssContent.get('action.email.inline')) and normalizeBoolean(ssContent.get('action.email.sendresults')):
            resultsHTML = htmlResultsTemplate().render(
                include_results_link=normalizeBoolean(ssContent.get('action.email.include.results_link')),
                results_link=ssContent.get('results_link'),
                truncated=normalizeBoolean(settings.get('truncated')),
                resultscount=len(results),
                jobcount=jobCount,
                hasjob=normalizeBoolean(settings.get('sid'))
            )
            format = ssContent.get('action.email.format') 
            if format == 'table':
                resultsHTML += htmlTableTemplate().render(results=results)
            elif format == 'raw':
                resultsHTML += htmlRawTemplate().render(results=results)
            elif format == 'csv':
                resultsHTML += htmlCSVTemplate().render(results=results)

    footerHTML = htmlFooterTemplate().render(footer=ssContent.get('action.email.footer.text'), re=re, filters=filters)
    wrapperHTML  = htmlWrapperTemplate().render(body=messageHTML+metaDataHTML+errorHTML+resultsHTML+footerHTML)

    email.attach(MIMEText(wrapperHTML, 'html', _charset=CHARSET))

def htmlWrapperTemplate():
    return template.Template('''
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    </head>
    <body style="font-size: 14px; font-family: helvetica, arial, sans-serif; padding: 20px 0; margin: 0; color: #333;">
        ${body}
    </body>
</html>
    ''')

def htmlMetaDataSSTemplate():
    return template.Template('''
<table cellpadding="0" cellspacing="0" border="0" class="summary" style="margin: 20px;">
    <tbody>
        % if view_link and name and include_view_link:
        <tr>
            <th style="font-weight: normal; text-align: left; padding: 0 20px 10px 0;">${ssType.capitalize()}:</th><td style="padding: 0 0 10px 0;"><a href="${view_link}" style=" text-decoration: none; margin: 0 40px 0 0; color: #5379AF;">${name|h}</a></td>
        </tr>
        % endif
        % if ssquery and include_search:    
        <tr>
            <th style="font-weight: normal; text-align: left; padding: 0 20px 10px 0;">Search String:</th><td style="padding: 0 0 10px 0;">${ssquery|h}</td>
        </tr>
        % endif
        % if include_trigger and name and alert_type and ssType == "alert":
        <tr>
            <th style="font-weight: normal; text-align: left; padding: 0 20px 10px 0;">Trigger:</th><td style="padding: 0 0 10px 0;">Saved Search [${name|h}]: ${alert_type}
                % if alert_type == "number of events":
                    (${jobcount})
                % endif
                </td>
        </tr>
        % endif
        % if include_trigger_time and trigger_timeHMS and trigger_date and ssType == "alert":
        <tr>
            <th style="font-weight: normal; text-align: left; padding: 0 20px 10px 0;">Trigger Time:</th><td style="padding: 0 0 10px 0;">${trigger_timeHMS} on ${trigger_date}.</td>
        </tr>
        % endif
    </tbody>
</table>
% if not include_inline:
    % if include_results_link:
    <a href="${results_link|h}" style=" text-decoration: none; margin: 0 20px; color: #5379AF;">View results</a>
    % endif
% endif
''')

def htmlMetaDataViewTemplate():
    return template.Template('''
 <p><a href="${view_link}" style=" text-decoration: none; margin: 20px 40px 0 20px; color: #5379AF;">View dashboard</a></p>
''')

def htmlErrorTemplate():
    return template.Template('''
% if errors:
    <div style="border-top: 1px solid #ccc;"></div>
    % for error in errors:
        <p style="margin: 20px;">${error|h}</p>
    % endfor
% endif
''')

def htmlResultsTemplate():
    return template.Template('''
<div style="margin-top: 10px; padding-top: 20px; border-top: 1px solid #ccc;"></div>
% if truncated:
    %if jobcount:  
<p style="margin: 0 20px;">Only the first ${resultscount} of ${jobcount} results are included below. 
    %else:
<p style="margin: 0 20px;">Search results in this email have been truncated. 
    %endif
    %if include_results_link:
<a href="${results_link|h}" style=" text-decoration: none; margin: 0 0; color: #5379AF;">View all results</a> in Splunk.</p>
    %else:
</p>
    %endif
% elif include_results_link:
<div style="margin: 0 20px;">
    <a href="${results_link|h}" style=" text-decoration: none; color: #5379AF;">View results in Splunk</a>
</div>
% endif
''')

def htmlMessageTemplate():
    return template.Template('<div style="margin: 0 20px;">${msg|h}</div>')

def htmlFooterTemplate():
    return template.Template('''
<div style="margin-top: 10px; border-top: 1px solid #ccc;"></div>
<% footerEscaped = filters.html_entities_escape(footer) %>
<% footerBreaks = re.sub(r'\\r\\n?|\\n', '<br>', footerEscaped) %>
<p style="margin: 20px; font-size: 11px; color: #999;">${footerBreaks}</p>
''')

def htmlTableTemplate():
    return template.Template('''
% if len(results) > 0:
<div style="margin:0">
    <div style="overflow: auto; width: 100%;">
        <table cellpadding="0" cellspacing="0" border="0" class="results" style="margin: 20px;">
            <tbody>
                <% cols = [] %>
                <tr>
                % for key,val in results[0].items():
                    % if not key.startswith("_") or key == "_raw" or key == "_time":
                        <% cols.append(key) %>
                        <th style="text-align: left; padding: 4px 8px; margin-bottom: 0px; border-bottom: 1px dotted #ccc;">${key|h}</th>
                    % endif
                % endfor
                </tr>
                % for result in results:
                    <tr valign="top">
                    % for col in cols:
                        <td style="text-align: left; padding: 4px 8px; margin-top: 0px; margin-bottom: 0px; border-bottom: 1px dotted #ccc;">${result.get(col)|h}</td>
                    % endfor
                    </tr>
                % endfor
            </tbody>
        </table>
    </div>
</div>
% else:
        <div class="results" style="margin: 20px;">No results found.</div>
% endif
''')

def htmlRawTemplate():
    return template.Template('''
% if len(results) > 0:
    % if results[0].get("_raw"):
        <div style="margin: 20px;" class="events">
        % for result in results:
            <div class="event"style="border-bottom: 1px dotted #ccc; padding: 5px 0; font-family: monospace; word-break: break-all;">${result.get("_raw", "")|h}</div>
        % endfor
        </div>
    % else:
        <div> The results contain no "_raw" field.  Please choose another inline format (csv or table).</div>
    % endif
% else:
    <div class="results" style="margin: 20px;">No results found.</div>
% endif
''')

def htmlCSVTemplate():
    return template.Template('''
% if len(results) > 0:
    <div style="margin: 20px;">
    <% cols = [] %>
    % for key,val in results[0].items():
        % if not key.startswith("_") or key == "_raw" or key == "_time":
            <% cols.append(key) %>
        % endif
    % endfor
${','.join(cols)|h}<br/>
    % for result in results:
        <% vals = [] %>
        % for col in cols:
            <% vals.append(result.get(col))%>
        % endfor
${','.join(vals)|h}<br/>
    % endfor
    </div>
% else:
    <div class="results" style="margin: 20px;">No results found.</div>
% endif
''')

def buildPlainTextBody(ssContent, results, settings, email, jobCount):
    plainTextMsg = buildPlainTextMessage().render(msg=ssContent.get('action.email.message'))
    plainResults = ''
    plainTextMeta = ''
    plainError = ''
    if ssContent['type'] == 'view':
        plainTextMeta = buildPlainTextViewMetaData().render(
            view_link=ssContent.get('view_link')
        )
        plainError = buildPlainTextError().render(errors=ssContent.get('errorArray'))
    else:
        if ssContent['type'] != 'searchCommand':
            plainTextMeta    = buildPlainTextSSMetaData().render(
                jobcount=jobCount,
                results_link=ssContent.get('results_link'),
                include_results_link=normalizeBoolean(ssContent.get('action.email.include.results_link')),
                view_link=ssContent.get('view_link'),
                include_view_link=normalizeBoolean(ssContent.get('action.email.include.view_link')),
                name=ssContent.get('name'),
                include_search=normalizeBoolean(ssContent.get('action.email.include.search')),
                ssquery=ssContent.get('search'),
                alert_type=ssContent.get('alert_type'),
                include_trigger=normalizeBoolean(ssContent.get('action.email.include.trigger')),
                include_inline=normalizeBoolean(ssContent.get('action.email.inline')),
                include_trigger_time=normalizeBoolean(ssContent.get('action.email.include.trigger_time')),
                trigger_date=ssContent.get('trigger_date'),
                trigger_timeHMS=ssContent.get('trigger_timeHMS'),
                ssType=ssContent.get('type')
            )
        plainError = buildPlainTextError().render(errors=ssContent.get('errorArray'))
        # need to check aciton.email.sendresults for type searchCommand
        if normalizeBoolean(ssContent.get('action.email.inline')) and normalizeBoolean(ssContent.get('action.email.sendresults')):
            plainResults = plainResultsTemplate().render(
                include_results_link=normalizeBoolean(ssContent.get('action.email.include.results_link')),
                results_link=ssContent.get('results_link'),
                truncated=normalizeBoolean(settings.get('truncated')),
                resultscount=len(results),
                jobcount=jobCount,
                hasjob=normalizeBoolean(settings.get('sid'))
            )
            format = ssContent.get('action.email.format')
            if format == 'table':
                plainResults += plainTableTemplate(results, ssContent)
            elif format == 'raw':
                plainResults += plainRawTemplate().render(results=results)
            elif format == 'csv':
                plainResults += plainCSVTemplate(results)

    plainFooter = plainFooterTemplate().render(footer=ssContent.get('action.email.footer.text'))

    email.attach(MIMEText(plainTextMsg + plainTextMeta + plainError + plainResults + plainFooter, 'plain', _charset=CHARSET))

def buildPlainTextSSMetaData():
    return template.Template('''
 % if view_link and name and include_view_link:
${ssType.capitalize()} Title:      ${name}
${ssType.capitalize()} Location:   ${view_link}
% endif
% if ssquery and include_search:    
Search String:    ${ssquery}
% endif
% if include_trigger and name and alert_type and ssType == "alert":
    % if alert_type == "number of events":
Trigger:          Saved Search [${name}]: ${alert_type} (${jobcount})
    % else:
Trigger:          Saved Search [${name}]: ${alert_type}
    %endif
% endif
% if include_trigger_time and trigger_timeHMS and trigger_date and ssType == "alert":
Trigger Time:     ${trigger_timeHMS} on ${trigger_date}.
% endif
% if not include_inline:
    % if include_results_link:
View results:     ${results_link}
    % endif
%endif
''')

def buildPlainTextViewMetaData():
    return template.Template('''

View dashboard:     ${view_link}

''')

def buildPlainTextMessage():
    return template.Template('${msg}')

def plainFooterTemplate():
    return template.Template('''
------------------------------------------------------------------------

${footer}
''')

def buildPlainTextError():
    return template.Template('''
% if errors:
------------------------------------------------------------------------
    % for error in errors:
${error}
    % endfor
% endif
''')

def plainResultsTemplate():
    return template.Template('''
------------------------------------------------------------------------
% if truncated:
    % if jobcount:
Only the first ${resultscount} of ${jobcount} results are included below.
    % else:
Search results in this email have been truncated.
    % endif
    % if include_results_link:
View all results in Splunk: ${results_link}
    % endif
% elif include_results_link:
View results in Splunk: ${results_link}
% endif
''')

# sort columns from shortest to largest
def getSortedColumns(results, width_sort_columns):
    if len(results) == 0:
        return []

    columnMaxLens = {}
    for result in results:
        for k,v in result.items():
            # ignore attributes that start with "_"
            if k.startswith("_") and k!="_raw" and k!="_time":
                continue
            newLen = len(str(v))
            oldMax = columnMaxLens.get(k, -1)
            
            #initialize the column width to the length of header (name)
            if oldMax == -1:
                columnMaxLens[k] = oldMax = len(k)
            if newLen > oldMax:
                columnMaxLens[k] = newLen

    colsAndCounts = []
    # sort columns iff asked to
    if width_sort_columns:
       colsAndCounts = columnMaxLens.items()
       colsAndCounts.sort(numsort)
    else:
       for k,v in results[0].items():         
          if k in columnMaxLens:
             colsAndCounts.append([k, columnMaxLens[k]]) 

    return colsAndCounts

def plainTableTemplate(results, ssContent):
    if len(results) > 0:
        width_sort_columns = normalizeBoolean(ssContent.get('action.email.width_sort_columns', True))
        columnMaxLens = getSortedColumns(results, width_sort_columns)
        text = ""
        space = " "*4
        
        # output column names
        for col, maxlen in columnMaxLens:
            val = col
            padsize = maxlen - len(val)
            text += val + ' '*padsize + space
        text += "\n" + "-"*len(text) + "\n"
        # output each result's values
        for result in results:
            for col, maxlen in columnMaxLens:
                val = result.get(col, "")
                padsize = maxlen - len(val)
                # left justify ALL the columns
                text += val + ' '*padsize + space
            text += "\n"
    else:
        text = "No results found."
    return text

def plainCSVTemplate(results):
    text = ""
    if len(results) > 0:
        cols = []
        for key,val in results[0].items():
            if not key.startswith("_") or key == "_raw" or key == "_time":
                cols.append(key)   
        text = ','.join(cols) +'\n'   
        for result in results:
            vals = []
            for col in cols:
                vals.append(result.get(col))
            text += ','.join(vals) + '\n'
    else:
        text = "No results found."
    return text

def plainRawTemplate():
    return template.Template('''
% if len(results) > 0:
    % if results[0].get('_raw'):
        % for result in results:
${result.get("_raw", "")}\n
        % endfor
    % else:
The results contain no "_raw" field.  Please choose another inline format (csv or table).
    % endif
% else:
No results found.
% endif
''')


def buildAttachments(settings, ssContent, results, email, jobCount):
    ssContent['errorArray'] = []
    sendpdf     = normalizeBoolean(ssContent.get('action.email.sendpdf', False))
    sendcsv     = normalizeBoolean(ssContent.get('action.email.sendcsv', False))
    sendresults = normalizeBoolean(ssContent.get('action.email.sendresults', False))
    inline      = normalizeBoolean(ssContent.get('action.email.inline', False))
    inlineFormat= ssContent.get('action.email.format')
    type        = ssContent['type']

    namespace   = settings['namespace']
    owner       = settings['owner']
    sessionKey  = settings['sessionKey']
    searchid    = settings.get('sid')
    
    pdfview      = ssContent.get('action.email.pdfview', '')
    subject      = ssContent.get("action.email.subject")
    ssName       = ssContent.get("name")
    server       = ssContent.get('action.email.mailserver', 'localhost')
    results_link = ssContent.get('results_link')
    
    paperSize        = ssContent.get('action.email.reportPaperSize', 'letter')
    paperOrientation = ssContent.get('action.email.reportPaperOrientation', 'portrait')

    pdfService  = None
    pdf         = None

    if sendpdf:

        import splunk.pdf.availability as pdf_availability
        pdfService = pdf_availability.which_pdf_service(sessionKey=sessionKey, viewId=pdfview, namespace=namespace, owner=owner)
        logger.info("sendemail pdfService = %s" % pdfService)

        try:
            if pdfService is "pdfgen":
                # will raise an Exception on error
                pdf = generatePDF(server, subject, searchid, settings, pdfview, ssName, paperSize, paperOrientation)
            elif pdfService is "deprecated":
                # will raise an Exception on error
                pdf = generatePDF_deprecated(results_link, subject, searchid, settings, pdfview, paperSize, paperOrientation)

        except Exception, e:
            logger.error("An error occurred while generating a PDF: %s" % e)
            ssContent['errorArray'].append("An error occurred while generating the PDF. Please see python.log for details.")

        if pdf:
            email.attach(pdf) 
    # (type == searchCommand and sendresults and not inline) needed for backwards compatibility
    # (sendresults and not(sendcsv or sendpdf or inline) and inlineFormat == 'csv') 
    #       needed for backwards compatibility when we did not have sendcsv pre 6.1 SPL-79561
    if sendcsv or (type == 'searchCommand' and sendresults and not inline) or (sendresults and not(sendcsv or sendpdf or inline) and inlineFormat == 'csv'):
        csvAttachment = MIMEBase("text", "csv")
        csvAttachment.set_payload(generateCSVResults(results))
        csvAttachment.add_header('Content-Disposition', 'attachment', filename="splunk-results.csv")
        email.attach(csvAttachment)
        if normalizeBoolean(settings.get('truncated')):
            if normalizeBoolean(len(results)) and normalizeBoolean(jobCount):
                ssContent['errorArray'].append("Only the first %s of %s results are included in the attached csv." %(len(results), jobCount))
            else:
                ssContent['errorArray'].append("Attached csv results have been truncated.")

def esc(val):
    return val.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    
def generateCSVResults(results):
    if len(results) == 0:
        return ''
    
    header = []
    s      = cStringIO.StringIO()
    w      = csv.writer(s)
    
    
    if "_time" in results[0] : header.append("_time")
    if "_raw"  in results[0] : header.append("_raw")
    
    # for backwards compatibility remove all internal fields except _raw and _time
    for k in results[0].keys():
       if k.startswith("_") :
          continue
       header.append(k)
        

    w.writerow(header)
    # output each result's values
    for result in results:
        row = [esc(result.get(col,"")) for col in header]
        w.writerow(row)
    return s.getvalue()

def generatePDF(serverURL, subject, sid, settings, pdfViewID, ssName, paperSize, paperOrientation):
    """
    Reach out and retrieve a PDF copy of the search results if possible
    and return the MIME attachment
    """
    sessionKey = settings.get('sessionKey', None)
    owner = settings.get('owner', 'nobody')
    if not sessionKey:
        raise PDFException("Can't attach PDF - sessionKey unavailable")

    # build up filename to use with attachments
    pdfViewID_filename = pdfViewID and pdfViewID.strip(' .:;|><\'"')
    datestamp = time.strftime('%Y-%m-%d')

    if pdfViewID_filename:
        filename = '%s-%s.pdf' % (pdfViewID_filename[:50], datestamp)
        # strip control characters, forward & backslash
        filename = re.sub(r'[\x00-\x1f\x7f/\\]+', '-', filename)
        if isinstance(filename, unicode):
            filename = filename.encode(CHARSET)
    else:
        filename = 'splunk-report-%s.pdf' % datestamp

    # build up parameters to the PDF server
    parameters = {}
    parameters['namespace'] = settings["namespace"]
    parameters['owner'] = owner
    if pdfViewID:
        parameters['input-dashboard'] = pdfViewID
    else:
        if ssName:
            parameters['input-report'] = ssName
        elif sid:
            # in the event where sendemail is called from search
            # and we need to generate pdf re-run the search 
            job = search.getJob(sid, sessionKey=sessionKey)
            jsonJob = job.toJsonable(timeFormat='unix')

            searchToRun = jsonJob.get('search').strip()
            if searchToRun.lower().startswith('search '):
                searchToRun = searchToRun[7:]

            sendemailRegex = r'\|\s*sendemail'
            if (re.findall(sendemailRegex, searchToRun)):
                parameters['input-search'] = re.split(sendemailRegex, searchToRun)[0]
                parameters['et'] = jsonJob.get('earliestTime')
                parameters['lt'] = jsonJob.get('latestTime')
            else:
                raise PDFException("Can't attach PDF - ssName and pdfViewID unavailable")

    if sid:
        if type(sid) is dict:
            for sidKey in sid:
                parameters[sidKey] = sid[sidKey]
        else:    
            parameters['sid'] = sid
    
    if paperSize and len(paperSize) > 0:
        if paperOrientation and paperOrientation != "portrait":
            parameters['paper-size'] = "%s-%s" % (paperSize, paperOrientation)
        else:
            parameters['paper-size'] = paperSize

    # determine if we should set an effective dispatch "now" time for this job
    scheduledJobEffectiveTime = getEffectiveTimeOfScheduledJob(settings.get("sid", ""))
    logger.info("sendemail:mail effectiveTime=%s" % scheduledJobEffectiveTime) 
    if scheduledJobEffectiveTime != None:
        parameters['now'] = scheduledJobEffectiveTime  
 
    try:
        # Ensure compatibility with systems with supportSSLV3Only=tru
        setSSLWrapProtocol(ssl.PROTOCOL_SSLv3) #not sure we need this now that we are using simpleRequest instead of urlopen
        response, content = simpleRequest("pdfgen/render", sessionKey = sessionKey, getargs = parameters, timeout = PDFGEN_SIMPLE_REQUEST_TIMEOUT)

    except splunk.SplunkdConnectionException, e:
        raise PDFException("Failed to fetch PDF (SplunkdConnectionException): %s" % str(e))

    except Exception, e:
        raise PDFException("Failed to fetch PDF (Exception type=%s): %s" % (str(type(e)), str(e)))

    if response['status']!='200':
        raise PDFException("Failed to fetch PDF (status = %s): %s" % (str(response['status']), str(content)))

    if response['content-type']!='application/pdf':
        raise PDFException("Failed to fetch PDF (content-type = %s): %s" % (str(response['content-type']), str(content)))

    mpart = MIMEApplication(content, 'pdf')
    mpart.add_header('content-disposition', 'attachment', filename=filename)
    logger.info('Generated PDF for email')
    return mpart

def getEffectiveTimeOfScheduledJob(scheduledJobSid):
    """ parse out the effective time from the sid of a scheduled job
        if no effective time specified, then return None
        scheduledJobSid is of form: scheduler__<owner>__<namespace>_<hash>_at_<epoch seconds>_<mS> """
    scheduledJobSidParts = scheduledJobSid.split("_")
    effectiveTime = None
    if "scheduler" in scheduledJobSidParts and len(scheduledJobSidParts) > 4 and scheduledJobSidParts[-3] == "at":
        secondsStr = scheduledJobSidParts[-2]
        try:
            effectiveTime = int(secondsStr)
        except:
            pass

    return effectiveTime

def generatePDF_deprecated(sslink, subject, searchid, settings, pdfview, paperSize, paperOrientation):
    """
    DEPRECATED
    generate a PDF using the old PDF server app
    
    Reach out and retrieve a PDF copy of the search results if possible
    and return the MIME attachment
    """
    sessionKey = settings.get('sessionKey', None)
    owner = settings.get('owner', 'nobody')
    logger.info('sslink=%s searchid=%s settings=%s' % (sslink, searchid, settings))
    if not (sslink and sessionKey):
        raise PDFException("Can't attach PDF - either ssLink or sessionKey unavailable")

    # send the report request to the appserver running on the host serving the content
    ss_scheme, ss_netloc, ss_path, ss_query, ss_fragment = urlparse.urlsplit(sslink)

    # Find the root prefix if the appserver is mounted on a prefix other than /
    prefix = ss_path[:ss_path.index('/app/')] 
    server = "%s://%s%s/en-US/report/" % (ss_scheme, ss_netloc, prefix)

    pdfviewfn = pdfview and pdfview.strip(' .:;|><\'"')

    datestamp = time.strftime('%Y-%m-%d')

    if pdfviewfn:
        filename = '%s-%s.pdf' % (pdfviewfn[:50], datestamp)
        # strip control characters, forward & backslash
        filename = re.sub(r'[\x00-\x1f\x7f/\\]+', '-', filename)
        if isinstance(filename, unicode):
            filename = filename.encode(CHARSET)
    else:
        filename = 'splunk-report-%s.pdf' % datestamp

    if pdfview:
        app = ss_path[len(prefix):].split('/')[2]
        target = "%s://%s%s/app/%s/%s" % (ss_scheme, ss_netloc, prefix, app, pdfview)
    else:
        # assume that no doc fragments are used here
        if ss_query:
            target = sslink + '&media=print'
        else:
            target = sslink + '?media=print'

    try:
        logger.info("sendemail opening PDF request to appserver at %s" % server)
        # Ensure compatibility with systems with supportSSLV3Only=tru
        setSSLWrapProtocol(ssl.PROTOCOL_SSLv3)
        response = urllib2.urlopen(server, urllib.urlencode({
            'request_path' : target,
            'session_key' : sessionKey,
            'owner': owner,
            'title' : subject,
            'papersize' : paperSize,
            'orientation' : paperOrientation
            }), PDF_REPORT_SERVER_TIMEOUT)
    except urllib2.HTTPError, e:
        msg = e.fp.read().strip()
        if msg and msg[0]=='>':
            raise PDFException("Failed to generate PDF: %s" % msg[1:])
        else:
            raise PDFException("Failed to contact appserver at %s: %s" % (server, e))
    except Exception, e:
        raise PDFException("Failed to fetch PDF from appserver at %s: %s" % (server, e))

    headers = response.info()
    if headers['Content-Type']!='application/pdf':
        logger.error("Didn't receive PDF from Report Server")
        raise PDFException("Didn't receive PDF from Report Server")

    data = response.read()
    mpart = MIMEApplication(data, 'pdf')
    mpart.add_header('content-disposition', 'attachment', filename=filename)
    logger.info('Generated PDF for email')
    return mpart

def getCredentials(sessionKey, namespace):
   try:
      ent = entity.getEntity('admin/alert_actions', 'email', namespace=namespace, owner='nobody', sessionKey=sessionKey)
      if 'auth_username' in ent and 'clear_password' in ent:
          return ent['auth_username'], ent['clear_password']
   except Exception, e:
      logger.error("Could not get email credentials from splunk, using no credentials. Error: %s" % (str(e)))

   return '', ''



results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
try:
    results = sendEmail(results, settings)
except Exception, e:
    logger.info(e)
splunk.Intersplunk.outputResults(results)
