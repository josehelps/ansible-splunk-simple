from django.conf.urls import patterns, include, url
from splunkdj.utility.views import render_template as render

urlpatterns = patterns('',
    url(r'^home/$', 'quickstartfx.views.home', name='home'), 
    url(r'^login/$', 'splunkdj.auth.views.login', {"template_name": "quickstartfx:login.html"}, name='login'), 
    url(
        r'^steps/credentials/$', 
        'splunkdj.auth.views.login',
        {'template_name': 'quickstartfx:credentials.html'}, 
        name='credentials'),
    url(r'^steps/(?P<id>.*)/$', 'quickstartfx.views.steps_view', name='steps'),
)
