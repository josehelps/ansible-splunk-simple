from django.template.base import (InvalidTemplateLibrary, libraries, Library, 
                                get_templatetags_modules, import_library, TemplateSyntaxError)
from django.template.defaulttags import LoadNode

register = Library()

@register.tag(name="import")
def import_taglib(parser, token):    
    """
    Extends Django's default {% load %} templatetag as a new tag called {% import %},
    which allows for extended functionality (while being backwards compatible).
    
    Load a tag library from a particular app:
        
        {% import myapp:mytaglib %}
    
    Load a particular tag from a particular app:
    
        {% import mytag from myapp:mytaglib %}
        
    Load a particular tag from a particular app and rename:
    
        {% import mytag from myapp:mytaglib as othername %}
        
    **Note**: you cannot rename multiple tags, so if you do:
    
        {% import mytag myothertag from myapp:mytaglib as othername %}
        
    then only the last tag will be using othername, and the first one won't
    be imported.
    """
    bits = token.contents.split()
    if (len(bits) >= 4 and bits[-2] == "from") or (len(bits) >= 6 and bits[-2] == "as"):
        lib_index = -1
        as_lib = None
        if (bits[-2] == "as"):
            lib_index = -3
            as_lib = bits[-1]
                        
        try:
            taglib = bits[lib_index]
            lib = get_library(taglib)
        except InvalidTemplateLibrary as e:
            raise TemplateSyntaxError("'%s' is not a valid tag library: %s" %
                                      (taglib, e))
        else:
            temp_lib = Library()
            for name in bits[1:(lib_index - 1)]:
                name_to_use = as_lib if as_lib else name
                if name in lib.tags:
                    temp_lib.tags[name_to_use] = lib.tags[name]
                    # a name could be a tag *and* a filter, so check for both
                    if name in lib.filters:
                        temp_lib.filters[name_to_use] = lib.filters[name]
                elif name in lib.filters:
                    temp_lib.filters[name_to_use] = lib.filters[name]
                else:
                    raise TemplateSyntaxError("'%s' is not a valid tag or filter in tag library '%s'" %
                                              (name, taglib))
            parser.add_library(temp_lib)
    else:
        for taglib in bits[1:]:
            # add the library to the parser
            try:
                lib = get_library(taglib)
                parser.add_library(lib)
            except InvalidTemplateLibrary as e:
                raise TemplateSyntaxError("'%s' is not a valid tag library: %s" %
                                          (taglib, e))
    return LoadNode()

def get_library(library_name):
    """
    An extension to Django's django.template.base.get_library, which allows
    tags to be loaded from specific apps using the 'app:taglib' syntax.
    
    So if in 'app1' you had templatetags/foo.py, you could load it as:
        
        {% import app1:foo %}
        
    or if you wanted to load a specific tag:
    
        {% import mytag from app1:foo %}
        
    This uses the same syntax as referencing URL patterns from specific
    apps, and does not clash with the '.' notation already used for loading
    modules within templatetags (e.g. templatetags/news/posts.py as news.posts).
    
    Without this functionality, Django template tags become a global namespace 
    issue, where different apps can easily clash with one another.
    """
    # Extract the specific information regarding the app and module from 
    # the library name, and calculate the fully qualified name.
    app_name = ""
    
    tagparts = library_name.split(":")
    if len(tagparts) > 1:
        app_name = tagparts[0]
        library_name = tagparts[1]
        qualified_library_name = "%s:%s" % (app_name, library_name)
    else:
        library_name = tagparts[0]
        qualified_library_name = library_name
        
    # See if it exists in the cache
    lib = libraries.get(qualified_library_name, None) 
    
    # If it isn't, we're going to look. Even though we know which app we want
    # to load it from, we're going to loop over the all modules to avoid 
    # introducing significant new code, and since the result is going to be 
    # cached.
    if not lib:
        templatetags_modules = get_templatetags_modules()
        tried_modules = []
        for module in templatetags_modules:
            taglib_module = '%s.%s' % (module, library_name)
            tried_modules.append(taglib_module)
            lib = import_library(taglib_module)
            if lib:
                # We managed to load a library, but now we need to see if it is
                # from the right app. We can do that by finding out which app
                # it came from.
                if app_name:
                    lib_app = taglib_module[:taglib_module.index('.')]
                    lib_name = "%s:%s" % (lib_app, library_name)
                else:
                    lib_name = library_name
                
                # OK, is it the right one? If so, store it in the cache
                if lib_name == qualified_library_name:
                    libraries[lib_name] = lib
                    break
                    
            # Haven't found it yet, keep going.
            lib = None
            
        # If we don't find any, we throw an exception with the ones we've tried.
        if not lib:
            raise InvalidTemplateLibrary("Template library %s not found, "
                                         "tried %s" %
                                         (library_name,
                                          ','.join(tried_modules)))
    return lib