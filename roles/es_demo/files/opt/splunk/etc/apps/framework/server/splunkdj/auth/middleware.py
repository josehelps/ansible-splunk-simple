from splunkdj.utility import create_derived_service, get_current_app_name
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import SimpleLazyObject

class SplunkAuthenticationMiddleware(object):
    def process_request(self, request):
        request.service = SimpleLazyObject(lambda: _get_service_for_current_app(request))

def _get_service_for_current_app(request):
    if not hasattr(request, '_cached_service_for_current_app'):
        request._cached_service_for_current_app = create_derived_service(
            _get_service(request),
            owner='nobody',
            app=get_current_app_name(request))
    return request._cached_service_for_current_app

def _get_service(request):
    if not hasattr(request, '_cached_service'): 
        if hasattr(request.user, 'service'):
            request._cached_service = request.user.service
        else:
            request._cached_service = None
    return request._cached_service
