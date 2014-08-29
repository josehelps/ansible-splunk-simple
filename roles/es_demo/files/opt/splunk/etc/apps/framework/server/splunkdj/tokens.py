from django.utils.safestring import SafeData, SafeUnicode
from xml.sax.saxutils import quoteattr

# Django assumes the UTF-8 encoding by default.
_ASSUMED_ENCODING = 'utf-8'

class TokenSafeString(SafeUnicode):
    """
    Wraps a string to mark it to be interpreted as a template
    that needs to be substituted. This substitution happens
    client-side in JavaScript.
    """
    
    def __new__(cls, value):
        # Force input to be Unicode if not already.
        if isinstance(value, str):
            value = value.decode(_ASSUMED_ENCODING)
        
        # Define the HTML-encoded version of this value
        # that will be used if this string is substituted
        # directly into an HTML template.
        s = SafeUnicode.__new__(cls,
            u'<span class="splunk-tokensafe" data-value=' + 
            quoteattr(value.encode(_ASSUMED_ENCODING)) + 
            u'></span>'
        )
        
        # Keep the original value for further processing 
        # in case a token-aware tag receives a TokenSafeString
        # as an attribute.
        s.value = value
        
        return s
