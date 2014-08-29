from django.contrib.auth.models import AbstractUser
from splunklib.client import connect, Service
import requests
import os, time

from django.conf import settings
from encryption import SimplerAES

import logging

logger = logging.getLogger('spl.django.service')

aes = SimplerAES(settings.SECRET_KEY)

def get_splunkweb_url(path):
    splunkweb_mount = ""
    if settings.SPLUNK_WEB_MOUNT:
        splunkweb_mount = "%s/" % settings.SPLUNK_WEB_MOUNT
        
    return "%s://%s:%s/%s%s" % (settings.SPLUNK_WEB_SCHEME, settings.SPLUNK_WEB_HOST, settings.SPLUNK_WEB_PORT, splunkweb_mount, path)

def logout_user(cookies, username):
    try:
        logger.info("%s logging out."% username)
        r1 = requests.get(
            get_splunkweb_url("account/logout"),
            allow_redirects=True,
            cookies=cookies)
    except Exception, e:
        logger.exception(e)
        pass

class SplunkUser(AbstractUser):
    def __init__(self, id=None, splunkweb=None, service=None, tz=None, realname="", is_free=False, *args, **kwargs):
        super(SplunkUser, self).__init__(*args, **kwargs)
        
        self.id = id
        self.splunkweb = splunkweb
        self.realname = realname
        self.service = service
        self.tz = tz
        self.is_free = is_free
            
    def save(self, *args, **kwargs):
        logger.debug("Failed to save SplunkUser: Function not implemented.")
        pass

class SplunkWebInfo(object):
    def __init__(self, cookies):
        self.session_id = cookies['session_id_%s' % settings.SPLUNK_WEB_PORT]
        self.cval = cookies['cval']
        self.uid = cookies['uid']

def get_user(username, token):
    if not username or not token:
        return None
    
    user = None
    properties = {}
    is_free = False
    try:
        service = Service(
            username=username, 
            token=token, 
            scheme=settings.SPLUNKD_SCHEME,
            host=settings.SPLUNKD_HOST,
            port=settings.SPLUNKD_PORT
        )
        
        server_info = service.info
        
        if (server_info.get('isFree', '0') == '0'):
            user = service.users[username]
            properties = user.content()
        else:            
            is_free = True
            properties = {
                "email": "nouser@splunkfree.com",
                "roles": ["admin"],
                "realname": "Administrator",
                "tz": None
            }
        
    except Exception, e:
        if hasattr(e, 'status') and e.status == 401:
            logger.error("Failed to get user: %s. Server returned 401: Unauthorized." % username)
            return None
        elif settings.DEBUG:
            logger.exception(e)
            raise
        else:
            logger.exception(e)
            return None
    
    
    user_id = "%s:%s" % (username, token)
    user_id = aes.encrypt(str(user_id))
    
    return SplunkUser(
        id=user_id,
        service=service,
        username=username,
        email=properties["email"],
        is_superuser="admin" in properties["roles"],
        is_staff="admin" in properties["roles"],
        is_active=True,
        is_free=is_free,
        realname=properties["realname"],
        tz=properties['tz']
    )

class SplunkAuthenticationBackend(object):
    supports_inactive_user = False
    
    def authenticate(self, username=None, password=None, *args, **kwargs):  
        try:
            logger.info("%s attempting to connect to Splunk server at %s:%s"%
                        (username, settings.SPLUNKD_HOST, settings.SPLUNKD_PORT) )           
            service = connect(
                username=username,
                password=password,
                scheme=settings.SPLUNKD_SCHEME,
                host=settings.SPLUNKD_HOST,
                port=settings.SPLUNKD_PORT
            )
        except Exception, e:
            if hasattr(e, 'status') and e.status == 401:
                logger.error("Failed to connect. Server returned 401: Unauthorized." % username)
                return None
            else:
                logger.exception(e)
                raise
        
        user = service.users[username]
        properties = user.content()
        user_id = "%s:%s" % (username, service.token)
        user_id = aes.encrypt(str(user_id))
        
        splunkweb_info = None
    
        try:
            r1 = requests.get(
                get_splunkweb_url("account/login"),
                allow_redirects=True)
            
            cval = r1.cookies['cval']
            r = requests.post(
                r1.url,
                cookies=r1.cookies,
                data={"username":username, "password":password, "cval":cval})
            
            splunkweb_info = SplunkWebInfo(r.cookies)
        except Exception, e:
            logger.exception(e)
            pass
        
        # JIRA: DVPL-3312
        return SplunkUser(
            id=user_id,
            splunkweb=splunkweb_info,
            service=service,
            username=username, 
            password=password, 
            email=properties["email"],
            is_superuser="admin" in properties["roles"],
            is_staff="admin" in properties["roles"],
            is_active=True,
            realname=properties["realname"],
            tz=properties['tz']
        )
        
    def get_user(self, user_id, *args, **kwargs):
        username = None
        token = None
        try:
            user_id = aes.decrypt(user_id)
            parts = user_id.split(":")
            username = parts[0]
            token = parts[1]
        except Exception, e:
            logger.exception(e)
            return None
        
        return get_user(username, token)
