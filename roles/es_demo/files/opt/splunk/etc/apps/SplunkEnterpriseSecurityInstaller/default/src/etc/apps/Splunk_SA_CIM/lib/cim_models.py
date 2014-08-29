'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import json
import splunk
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field

class DataModels(SplunkAppObjModel):
    '''Class for data model json'''

    resource = '/data/models'

    data = Field(api_name="eai:data")
    baseObjects = ['BaseEvent', 'BaseSearch', 'BaseTransaction']

    @staticmethod
    def stripBaseObject(lineage, outputMode='basestring'):
        ## this takes lineage as a list or string
        ## always returns string
        if len(lineage)>0:
            if isinstance(lineage, basestring):
                lineage = lineage.split('.')
            
            if lineage[0] in DataModels.baseObjects:
                lineage = lineage[1:len(lineage)]

            if outputMode=="list":
                return lineage
            else:
                return '.'.join(lineage)

        return ''

    @staticmethod
    def getObjectLineage(objectName, modelJson, includeBaseObject=False):
        parents = {obj['objectName']: obj['parentName'] for obj in modelJson['objects']}
        lineage = []
        tmp = objectName
    
        if tmp in parents:
            while tmp in parents:
                lineage.append(tmp)
                tmp = parents[tmp]
            if includeBaseObject:
                lineage.append(tmp)    
            lineage.reverse()
            return '.'.join(lineage)
        else:
            return ''

    @staticmethod
    def getDatamodelList(sessionKey):
        if not sessionKey:
            raise splunk.AuthenticationFailed
       
        return [model.name for model in DataModels.all(sessionKey=sessionKey)]

    @staticmethod
    def getDatamodelObjectList(datamodel, sessionKey, baseEventOnly=False):
        if not sessionKey:
            raise splunk.AuthenticationFailed
        
        objects = []
        
        ## get the model
        model_id = DataModels.build_id(datamodel, None, None)
        model = DataModels.get(id=model_id, sessionKey=sessionKey)
        
        ## load the json
        modelJson = json.loads(model.data)
        
        if modelJson.get('objects', False):
            for object in modelJson['objects']:
                if object.get('objectName', False):
                    objectName = object['objectName']
                    
                    if baseEventOnly:
                        objectLineage = DataModels.getObjectLineage(objectName, modelJson, includeBaseObject=True)
                        if objectLineage.startswith('BaseEvent'):
                            objects.append(objectName)
                    
                    else:    
                        objects.append(objectName)

        return objects
    
    @staticmethod
    def getObjectAttributes(objectName, modelJson):
        attributes = []
        
        for obj in modelJson['objects']:
            if obj.get('objectName', None) == objectName:
                for field in obj.get('fields', []):
                    attributes.append(field.get('fieldName', []))
                for fields in [calc.get('outputFields') for calc in obj.get('calculations', {})]:
                    attributes.extend([field.get('fieldName', []) for field in fields ])
        
        return attributes        