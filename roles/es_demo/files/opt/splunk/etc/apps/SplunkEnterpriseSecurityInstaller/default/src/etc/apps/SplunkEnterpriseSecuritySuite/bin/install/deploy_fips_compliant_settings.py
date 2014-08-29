import splunk
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import BoolField
from splunk.models.field import Field
from . import isFipsEnabled


class SplunkApp(SplunkAppObjModel):
    '''Minimal class for retrieving Splunk applications.'''
    resource = '/apps/local'
    configured = BoolField()
    name = Field()


class SplunkDataModel(SplunkAppObjModel):
    '''Minimal class for retrieving Splunk applications.'''
    resource = '/datamodel/model'
    description = Field()  # JSON description of the model.
    name = Field()
    provisional = BoolField()  # Set to True to validate the model before saving.


class SplunkLookupTableFile(SplunkAppObjModel):
    '''Minimal class for retrieving Splunk lookup table files.'''
    resource = '/data/lookup-table-files'
    name = Field()
    path = Field(api_name="eai:data")


class SplunkLookupTransform(SplunkAppObjModel):
    '''Minimal class for Splunk lookups as defined in transforms.conf.'''
    resource = '/data/transforms/lookups'
    filename = Field()
    name = Field()


class SplunkMacro(SplunkAppObjModel):
    '''Minimal class for Splunk macros as defined in macros.conf.'''
    resource = '/configs/conf-macros'
    name = Field()
    definition = Field()


def set_conf(cls, name, namespace, owner, key, **postargs):
    entity_id = cls.build_id(name, namespace, owner)
    entity = cls.manager()._put_args(entity_id, postargs, sessionKey=key)
    return entity


def isLookupEmpty(lookup_name, namespace, owner, key):
    transform = SplunkLookupTransform.get(SplunkLookupTransform.build_id(lookup_name, namespace, owner), sessionKey=key)
    # Path will be a full path.
    path = SplunkLookupTableFile.get(SplunkLookupTableFile.build_id(transform.filename, namespace, owner), sessionKey=key).path
    
    # Just validate that the file has more than a header line. 
    for lineno, line in enumerate(open(path, 'r')):
        if lineno > 1:
            return False
    return True


def set_fips_macro(fips_alg, logger, key):
    # Set hash_alg macro definition if not already set.
    model = SplunkMacro.get(SplunkMacro.build_id('hash_alg', 'SA-Utils', 'nobody'), key)
    if model.definition != fips_alg:
        logger.info('Updating hash algorithm in hash_alg macro: old="%s" new="%s"', model.definition, fips_alg)
        newmodel = set_conf(SplunkMacro, 'hash_alg', 'SA-Utils', 'nobody', key, **{'definition': fips_alg})
    else:
        logger.info('Hash algorithm already set correctly in hash_alg macro: old="%s" new="%s"', model.definition, fips_alg)


def set_fips_incident_management(old_alg, fips_alg, logger, key):
    # Set hash algorithm in Incident Review data model if not already set correctly.
    model = SplunkDataModel.get(SplunkDataModel.build_id('Incident_Management', 'SA-ThreatIntelligence', 'nobody'), key)
    if old_alg in model.description:
        logger.info('Updating hash algorithm in Incident Management data model')
        newmodel = set_conf(SplunkDataModel, 'Incident_Management', 'SA-ThreatIntelligence', 'nobody', key, **{'description': model.description.replace(old_alg, fips_alg)})
    else:
        logger.info('Hash algorithm already set correctly in Incident Management data model')


def deployFips(key, logger):
    '''Update macros to use FIPS-compliant hash algorithms.'''
    DEFAULT_APP = 'SplunkEnterpriseSecuritySuite'
    DEFAULT_OWNER = 'nobody'
    IR_LOOKUP = 'incident_review_lookup'
    
    fips_enabled = False
    incident_review_empty = False

    try:
        fips_enabled = isFipsEnabled()
        incident_review_empty = isLookupEmpty(IR_LOOKUP, DEFAULT_APP, DEFAULT_OWNER, key)

        if fips_enabled and incident_review_empty:
            set_fips_macro('sha1', logger, key)
            set_fips_incident_management('md5', 'sha1', logger, key)
        else:
            if not incident_review_empty:
                logger.error('Enterprise Security setup has been run on a Splunk instance that was converted to FIPS compliance after first startup. This is not supported.')
            elif not fips_enabled:
                logger.info('FIPS not enabled... non-FIPS-compliant hash algorithms will be used in some calculations.')
            
    except Exception:
        logger.exception('msg="Error updating FIPS compliance settings."')
