from django.core.exceptions import ValidationError
from django.forms import Field as _Field
from django.forms import Form as _Form
import inspect
from splunklib.binding import UrlEncoded
from splunklib.client import Entity
import urllib

def wrap_field_class(DjangoField):
    """
    Mixes in data binding functionality to an existing forms.Field class.
    """
    class SplunkField(DjangoField):
        """
        Extends Django's forms.Field class with built-in data binding
        against the Splunk REST API (and custom loaders/savers).
        """
        def __init__(self,
                endpoint=None, entity=None, field=None,
                load=None, save=None,
                *args, **kwargs):
            """
            One of the following parameter sets must be provided in addition
            to the normal required parameters of the field:
            
            (1) Persistence to Splunk REST API
                * endpoint -- URL to a collection endpoint in the Splunk REST API.
                * entity -- Name of an entity to access. This name is not URL encoded.
                * field -- Name of a field on the entity to access. This name is not URL encoded.
            
            (2) Persistence to Custom Data Store
                * load -- Callable that takes (request, form_cls, field)
                          and returns the persisted value for the field.
                * save -- Callable that takes (request, form_cls, field, value)
                          and persists the specified value.
            
            Most custom load and save functions will want to extract the 
            splunklib.Service object from the provided Request object via
            `request.service`.
            """
            super(SplunkField, self).__init__(*args, **kwargs)
            
            if (endpoint, entity, field) != (None, None, None):
                if endpoint is None:
                    raise ValueError('Expected "endpoint" keyword argument.')
                if entity is None:
                    raise ValueError('Expected "entity" keyword argument.')
                if field is None:
                    raise ValueError('Expected "field" keyword argument.')
                self._endpoint = endpoint
                self._entity_name = entity
                self._field_name = field
                self._load = None
                self._save = None
            elif (load, save) != (None, None):
                if load is None:
                    raise ValueError('Expected "load" keyword argument.')
                if save is None:
                    raise ValueError('Expected "save" keyword argument.')
                self._load = load
                self._save = save
            else:
                raise ValueError(
                    'Expected either the keyword arguments ' +
                    '{"endpoint", "entity", "field"} or {"load", "save"}.')
        
        def load(self, request, form_cls):
            """Loads this field's persisted value, returning the value."""
            
            if self._load is not None:
                return self._load(request, form_cls, self)
            
            entity = self._get_entity(request.service)
            return entity[self._field_name]
        
        def save(self, request, form, value):
            """Saves this field's persisted value."""
            
            if self._save is not None:
                self._save(request, form, self, value)
                return
            
            entity = self._get_entity(request.service)
            entity.update(**{
                self._field_name: value
            })
        
        def _get_entity(self, service):
            return Entity(service, UrlEncoded(self._entity_path, skip_encode=True))
        
        @property
        def _entity_path(self):
            return '%s/%s' % (self._endpoint, urllib.quote_plus(self._entity_name))
    
    return SplunkField

def wrap_fields_in_module(module_dict):
    """
    Mixes in data binding functionality to all forms.Fields declared
    in the specified module.
    """
    for (var_name, var_value) in dict(module_dict).iteritems():
        # _Field is the original django.forms.Field. Don't wrap it.
        if var_name == '_Field':
            continue
        if inspect.isclass(var_value) and issubclass(var_value, _Field):
            module_dict[var_name] = wrap_field_class(var_value)

class _SplunkForm(_Form):
    """
    Extends Django's forms.Form class with built-in data binding
    against the Splunk REST API (and custom loaders/savers).
    """
    @classmethod
    def load(cls, request):
        """Loads this form's persisted state, returning a new Form."""
        
        cls._validate_form_fields()
        
        settings = {}
        for (field_name, field) in cls.base_fields.iteritems():
            raw_value = field.load(request, cls)
            # Try to normalize the value
            try:
                cleaner_value = field.clean(raw_value)
            except ValidationError:
                cleaner_value = raw_value
            settings[field_name] = cleaner_value
        return cls(settings)
    
    def save(self, request):
        """Saves this form's persisted state."""
        
        type(self)._validate_form_fields()
        
        settings = self.cleaned_data
        for (field_name, field) in self.base_fields.iteritems():
            settings[field_name] = field.save(request, self, settings[field_name])
        return settings
    
    @classmethod
    def _validate_form_fields(cls):
        # Validate that the form's fields have the expected "load" and "save"
        # extensions that are not present in stock Django fields.
        for (field_name, field) in cls.base_fields.iteritems():
            if not hasattr(field, 'load') or not hasattr(field, 'save'):
                raise ValueError(
                    ('Expected field "%s" of type %s on %s to have ' +
                     '"load" and "save" methods. ' +
                     'Was this declared as a django.forms.Field instead of as ' +
                     'a splunkdj.setup.forms.Field?') % (
                        field_name,
                        field.__class__.__name__,
                        cls.__name__))

# ------------------------------------------------------------------------------

# Allow this module to be a general drop-in replacement for django.forms
from django.forms import *

# Wrap all imported Field classes
wrap_fields_in_module(globals())

# Wrap the Form class
Form = _SplunkForm
