import os
import logging
import copy
import re

import splunk
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField, EpochField, IntField, ListField, FloatField, FloatByteField, IntByteField, DictField

logger = logging.getLogger('splunk.models.base')

class BaseModel(SplunkAppObjModel):
    """MVC Model wrapper with added functionality for common model operations"""
    
    # ordered list of fields making up unique composite key.
    # To bet overridden by subclass.  Default is single key 'name'
    uniqueCompositeKeyList = ['name']

    # atomic transaction flag
    _is_transaction = False
    # to keep track of dirty instances within a transaction
    _instances_created = []
    _instances_updated = []
    _instances_deleted = []

    def __init__(self, namespace, owner, name, sharing='app', entity=None, host_path=None, sessionKey=None, **kwargs):
        super(BaseModel, self).__init__(namespace, owner, name, entity,
                                        host_path=host_path, sessionKey=sessionKey, **kwargs)
        # default sharing for MVC models is app level unless otherwise specified
        self.metadata.sharing = sharing

    # /////////////////////////////////////////////////////////////////////////////
    #   BaseModel Utility methods
    # /////////////////////////////////////////////////////////////////////////////

    def to_jsonable(self):
        '''
        Returns a native structure that represents the current model.
        '''
 
        output = {
            'name': self.name
        }
        for k in self.get_mutable_fields():
            output[k] = getattr(self, k)
        
        return output

    def get_unique_key(self):
        '''
        Returns model's unique key
        '''

        key = '|'.join(map(lambda k: getattr(self, k, ""), self.uniqueCompositeKeyList))
        return key

    def is_new(self):
        '''
        Returns True is model is new (distinguish create vs update).
        '''

        return not self.id

    # /////////////////////////////////////////////////////////////////////////////
    #   BaseModel Transaction methods
    # /////////////////////////////////////////////////////////////////////////////

    @classmethod
    def start_transaction(cls):
        '''
        Start atomic transaction. All instances created/updated/deleted
        will be tracked until until end_transaction(), in case of a rollback.
        '''

        if cls._is_transaction:
            raise Exception, 'transaction already started'
        if (len(cls._instances_created) > 0) or \
            (len(cls._instances_updated) > 0) or \
            (len(cls._instances_deleted) > 0):
            raise Exception, 'internal error: saved state must be empty at transaction start'
        cls._is_transaction = True

    @classmethod
    def end_transaction(cls):
        '''
        End atomic transaction.
        '''

        cls._is_transaction = False
        # reset saved states
        del cls._instances_created[:]
        del cls._instances_updated[:]
        del cls._instances_deleted[:]

    @classmethod
    def rollback(cls):
        '''
        Roll back all instances created/edited/deleted in current transaction.
        This gets triggered upon any save/delete error during transaction.
        '''

        logger.debug('rollback instances')
        logger.debug('num instances created: %s' % len(cls._instances_created))
        logger.debug('num instances updated: %s' % len(cls._instances_updated))
        logger.debug('num instances deleted: %s' % len(cls._instances_deleted))

        # mark transaction complete
        cls._is_transaction = False
        result = True
        try:
            # delete created instances
            while len(cls._instances_created) > 0:
                instance = cls._instances_created.pop(0)
                logger.debug('rolling back instance %s' % instance.name)
                if not instance.delete():
                    result = False
                    logger.error('rolling back: failed to delete new instance %s' % instance.name)
            # revert updated instances
            while len(cls._instances_updated) > 0:
                instance = cls._instances_updated.pop(0)
                logger.debug('rolling back instance %s' % instance.name)
                #print instance.__dict__
                #print getattr(instance, 'args')
                if not instance.passive_save():
                    result = False
                    logger.error('rolling back: failed to revert instance %s: %s' % (instance.name, instance.errors[0]))
            # aad deleted instances
            while len(cls._instances_deleted) > 0:
                instance = cls._instances_deleted.pop(0)
                instance.id = None
                # instance = cls(original.namespace, original.owner, original.name)
                # instance.update(original.to_jsonable())
                logger.debug('rolling back instance %s' % instance.name)
                if not instance.passive_save():
                    result = False
                    logger.error('rolling back: failed to add back instance %s: %s' % (instance.name, instance.errors[0]))
        finally:
            # end trx and reset saved state
            cls.end_transaction()

        return result

    # /////////////////////////////////////////////////////////////////////////////
    #   BaseModel Operations
    # /////////////////////////////////////////////////////////////////////////////

    def save(self, skip_validation=False):
        '''
        Override save to support object state callbacks & transaction.
        '''

        is_new = self.is_new()
        try:            
            if not skip_validation:
                # apply built-in validation
                self.__validate()
            
            # apply before save callback
            self.before_save()

            # if update during transaction, save instance state before update
            if self.__class__._is_transaction and (not is_new):
                # get currently saved instance
                original = self.__class__.get(self.__class__.build_id(self.name, self.namespace, self.owner))
                #original = self.__class__(self.namespace, self.owner, self.name, self.entity)
                #original.from_entity(self.entity)
                self.__class__._instances_updated.append(copy.copy(original))

            # actually save the instance
            result = super(BaseModel, self).save()
        except Exception, e:
            logger.error('error saving instance %s: %s' % (self.name, str(e)))
            if self.__class__._is_transaction:
                if not is_new:
                    self.__class__._instances_updated.pop()
                self.__class__.rollback()
            raise

        # if create during transaction, save newly created instance
        if self.__class__._is_transaction and is_new:
            self.__class__._instances_created.append(self)
        
        # manually set id as save doesn't update model id during create
        if self.is_new():
            self.id = self.__class__.build_id(self.name, self.namespace, self.owner)

        return result

    def passive_save(self, skip_validation=False):
        '''
        Returns a boolean over raising an exception and adds text message to error instance member. 
        NOTE: Flushes errors instance member before adding messages to avoid duplicate/stale entries.
        '''
        self.errors = []
        try:
            self.save(skip_validation)
        except Exception, e:
            error_filter = ['Bad Request']
            regex = re.compile("In handler '[^\']+':")
            self.errors = [re.sub(regex, '', x).lstrip() for x in self.parse_except_messages(e) if x not in error_filter]
            return False
        else:
            return True

    def delete(self):
        '''
        Override delete to support object state callbacks & transaction.
        '''

        try:
            # apply before delete callback
            self.before_delete()

            if self.__class__._is_transaction:
                self.__class__._instances_deleted.append(copy.copy(self))

            return super(BaseModel, self).delete()
        except Exception, e:
            logger.error('error deleting instance %s: %s' % (self.name, str(e)))
            if self.__class__._is_transaction:
                self.__class__.rollback()
            else:
                raise

    def set_fields(self, fields):
        '''
        Set model instance fields with specified fields.
        This serves as mass field assignment, and does not save the instance.
        '''
        return self.update(fields)

    def __validate(self):
        '''
        Raise exception if instance has duplicate key. Otherwise, return True.
        '''

        # build model unique key dict and ensure it does not exist already
        filter_dict = {}
        for field in self.uniqueCompositeKeyList:
            value = getattr(self, field, None)
            if not value:
                raise Exception, 'required field \'%s\' is missing' % field
            else:
                filter_dict[field] = getattr(self, field)

        if self.metadata.sharing == 'app':
            dups = self.__class__.all().filter_by_app(self.namespace).filter(**filter_dict)
        elif self.metadata.sharing == 'user':
            dups = self.__class__.all().filter_by_app(self.namespace).filter_by_user(self.owner).filter(**filter_dict)
        elif self.metadata.sharing == 'global':
            dups = self.__class__.all().filter(**filter_dict)
        else:
            raise Exception, 'invalid sharing level: %s' % self.metadata.sharing

        # return error if:
        #   1. creating new instance with a used key, or,
        #   2. updating old instance to same key of another instance
        if (len(dups) > 0) and (self.is_new() or dups[0].name != self.name):
            raise Exception, 'instance of same key %s already exists' %  self.get_unique_key()

        return True

    # /////////////////////////////////////////////////////////////////////////////
    #   BaseModel Callback hooks to be overridden
    # /////////////////////////////////////////////////////////////////////////////

    def before_save(self):
        '''
        Before save callback is triggered before self.save() or self.passive_save().
        '''

        return True

    def before_delete(self):
        '''
        Before delete callback is triggered before self.delete().
        '''

        return True
 
    # /////////////////////////////////////////////////////////////////////////////
    #   Sadly the core model doesn't implement saving permissions
    # /////////////////////////////////////////////////////////////////////////////   

    def save_metadata(self):
        '''
        Save metadata
        '''
        if not self.id:
            return False

        self.postargs = {}
        self.postargs['sharing'] = self.metadata.sharing
        self.postargs['owner']   = self.metadata.owner
        self.postargs['perms.read'] = self.metadata.perms['read']
        self.postargs['perms.write'] = self.metadata.perms['write']

        messages = []
        newEntity = self.manager()._put_args(self.id + "/acl", self.postargs,
                                             messages, sessionKey=self.sessionKey)

        if not newEntity:
            logger.error('base.py not newEntity: %s' % messages)
            return None

        self.entity = newEntity
        self.from_entity(self.entity)

        return True
