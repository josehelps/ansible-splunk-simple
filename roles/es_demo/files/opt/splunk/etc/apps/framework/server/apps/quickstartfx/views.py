from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from splunkdj.decorators.render import render_to

def home(request):
    if request.user and request.user.is_authenticated():
        return redirect('quickstartfx:steps', id="createApp")
    else:
        return redirect("quickstartfx:credentials") 

@render_to()
@login_required
def steps_view(request, id="createApp"):
    return {
        "TEMPLATE": "quickstartfx:%s.html" % id,
    }