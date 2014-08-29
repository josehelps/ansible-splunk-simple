import urlparse

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, QueryDict
from django.template.response import TemplateResponse
from django.utils.http import base36_to_int
from django.utils.translation import ugettext as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

# Avoid shadowing the login() and logout() views below.
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

from backends import logout_user

from encryption import SimplerAES
aes = SimplerAES(settings.SECRET_KEY)

# Use 'return_to' for interop with splunkweb
ORIGINAL_REDIRECT_FIELD_NAME=REDIRECT_FIELD_NAME
REDIRECT_FIELD_NAME = "return_to"

@sensitive_post_parameters()
@csrf_protect
def login(request, template_name=settings.LOGIN_TEMPLATE,
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the login action.
    """
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    
    if settings.SPLUNK_WEB_INTEGRATED:
        # In integrated mode, we don't do anything here, but when we redirect,
        # make sure we redirect using the return_to information.
        return HttpResponseRedirect(settings.LOGIN_URL + "?%s=%s" % (redirect_field_name, redirect_to))
        
    if not redirect_to:
        redirect_to = request.REQUEST.get(ORIGINAL_REDIRECT_FIELD_NAME, '')

    if request.method == "POST":
        form = authentication_form(data=request.POST, request=request)
        if form.is_valid():
            netloc = urlparse.urlparse(redirect_to)[1]

            # Use default setting if redirect_to is empty
            if not redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL

            # Heavier security check -- don't allow redirection to a different
            # host.
            elif netloc and netloc != request.get_host():
                redirect_to = settings.LOGIN_REDIRECT_URL

            # Okay, security checks complete. Log the user in.
            auth_login(request, form.get_user())

            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()

            redirectResponse = HttpResponseRedirect(redirect_to)
            
            # Get the user    
            user = form.get_user() 
        
            # Set the Splunkweb cookie values
            if user.splunkweb:
                session_id = user.splunkweb.session_id
                cval = user.splunkweb.cval
                uid = user.splunkweb.uid
                
                redirectResponse.set_cookie('session_id_%s' % settings.SPLUNK_WEB_PORT, session_id)
                redirectResponse.set_cookie('cval', cval)
                redirectResponse.set_cookie('uid', uid)
            
            # Set a standalone, encrypted cookie for the session key, so we can
            # access it in the proxy.
            session_token = user.service.token
            redirectResponse.set_cookie('session_token', aes.encrypt(str(session_token)))
            
            # Set the session cookie to expire when the browser is closed
            request.session.set_expiry(0)
            
            return redirectResponse
    else:
        form = authentication_form(request)

    request.session.set_test_cookie()

    context = {
        'form': form,
        redirect_field_name: redirect_to
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)
    
def logout(request, next_page=None,
           template_name='splunkdj:auth/registration/login.html',
           redirect_field_name=REDIRECT_FIELD_NAME,
           current_app=None, extra_context=None):
    """
    Logs out the user and displays 'You are logged out' message.
    """

    if settings.SPLUNK_WEB_INTEGRATED:
        return HttpResponseRedirect(settings.LOGOUT_URL)
        
    userName = getattr(request, 'user', '-')

    auth_logout(request)
    
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if redirect_to:
        netloc = urlparse.urlparse(redirect_to)[1]
        # Security check -- don't allow redirection to a different host.
        if not (netloc and netloc != request.get_host()):
            response = HttpResponseRedirect(redirect_to)
    else:
        response = HttpResponseRedirect(settings.LOGIN_URL)
    
    logout_user(request.COOKIES, userName)
    
    response.delete_cookie('session_id_%s' % settings.SPLUNK_WEB_PORT)
    response.delete_cookie('cval')
    response.delete_cookie('uid')
    
    return response        
    
