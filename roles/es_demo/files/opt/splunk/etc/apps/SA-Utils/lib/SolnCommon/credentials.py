'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
from splunk import AuthenticationFailed, ResourceNotFound

from .models import SplunkStoredCredential


class CredentialManager(object):
    
    def __init__(self, sessionKey=None):
        if sessionKey is None:
            raise AuthenticationFailed('A session key was not provided.')
        self._sessionKey = sessionKey
        
    def _build_id(self, user, realm):
        '''Helper method for creating the realm:user syntax used by the endpoint
        to specify the entity.'''
        return (realm or '') + ':' + user + ':'
                
    def get_clear_password(self, user, realm, app, owner):
        '''Get the clear-text password for a user and realm.
        
        @return: The decrypted form of the password.
        '''
        
        q = SplunkStoredCredential.get(SplunkStoredCredential.build_id(self._build_id(user, realm), app, owner), self._sessionKey)
        return q.clear_password

    def get_password(self, user, realm, app, owner):
        '''Get the password for a user and realm.
        
        @return: The encrypted form of the password.
        '''
        
        q = SplunkStoredCredential.get(SplunkStoredCredential.build_id(self._build_id(user, realm), app, owner), self._sessionKey)
        return q.encr_password
             
    def set_password(self, user, realm, password, app, owner):
        '''Update the password for a user and realm.
        
        @return: The encrypted password value.
        
        The POST method for this endpoint requires the syntax realm:user
        be appended to the URI, necessitating the use of _put_args.'''
        
        postargs = {'password': password}
        cred_id = SplunkStoredCredential.build_id(self._build_id(user, realm), app, owner)
        # _put_args returns an entity.
        cred = SplunkStoredCredential.manager()._put_args(cred_id, postargs, sessionKey=self._sessionKey)
        return cred['encr_password']
    
    def create(self, user, realm, password, app, owner):
        '''Create a new stored credential.
        
        @return: The encrypted password value.
        '''
        
        cred = SplunkStoredCredential(app, owner, user, sessionKey=self._sessionKey)

        if realm:
            cred.realm = realm
        cred.password = password
                
        if cred.create():
            return self.get_password(user, realm, app, owner)
        else:
            return None
    
    def create_or_set(self, user, realm, password, app, owner):
        """Create or update a credential in Splunk's secure credential store.
        
        @return: The encrypted password value.
        """
        
        try:
            exists = self.get_password(user, realm, app, owner)
            return self.set_password(user, realm, password, app, owner)
        except ResourceNotFound:
            return self.create(user, realm, password, app, owner)

    def delete(self, user, realm):
        raise NotImplementedError('Deletion not supported by this handler.')
