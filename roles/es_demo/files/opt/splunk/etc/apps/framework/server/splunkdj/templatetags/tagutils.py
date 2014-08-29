import json
from splunkdj.tokens import TokenSafeString

def component_context(context, type, id, component_type, require_file, kwargs, tag="div", classes=""):
    """Returns a component template context constructed from the given args."""
    
    options = { 'app': context['app_name'] }
    options.update(kwargs)
    
    options = dict((k, _encode_option_value(v)) for (k, v) in options.iteritems())
    
    return {
        "type": type,
        "tag": tag,
        "id": id,
        "component_type": component_type,
        "style": "display: none;" if component_type == "context" else "",
        "require_file": require_file,
        "options": json.dumps(options),
        "raw_options": options,
        "context": context
    }

def _encode_option_value(value):
    if isinstance(value, TokenSafeString):
        return {'type': 'token_safe', 'value': value.value}
    else:
        return value
