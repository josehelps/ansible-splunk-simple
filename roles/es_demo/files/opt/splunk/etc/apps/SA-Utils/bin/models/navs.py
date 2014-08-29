from sc_base_model import BaseModel
from splunk.models.field import Field, BoolField

class Nav(BaseModel):
    resource              = '/data/ui/nav'
    data                  = Field(api_name='eai:data')