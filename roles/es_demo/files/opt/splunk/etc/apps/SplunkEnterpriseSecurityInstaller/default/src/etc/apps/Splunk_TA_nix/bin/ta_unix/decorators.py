import cherrypy

def host_app(fn):

    def decorator(self, *args, **kwargs):
        kwargs.update({'host_app' : cherrypy.request.path_info.split('/')[3]})
        return fn(self, *args, **kwargs)
    
    return decorator

