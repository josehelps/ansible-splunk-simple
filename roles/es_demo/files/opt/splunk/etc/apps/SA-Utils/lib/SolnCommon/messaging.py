import sys

import splunk
import splunk.auth
import splunk.util

from splunk.models.message import Message


class Messenger:
    
    @classmethod
    def createMessage(cls, text, key, msgid=None, namespace='SA-Utils', owner='nobody', suppress=False):
        '''Creates a UI message.
        
        @param text: The message text.
        @param msgid: A unique identifier to use for identifying the message. One will
            be created if not provided as a parameter.
        @param namespace: A Splunk namespace for the message.
        @param owner: A Splunk owner for the message.
        
        @return: A unique identifier that can be used to remove the message,
            or None in the event that the message couldn't be created.
        '''

        if not suppress:
            msgid = msgid or splunk.util.uuid4()
            message = Message(namespace, owner, msgid, sessionKey=key)
            message.value = text
            
            success = message.passive_save()
            
            if success:
                return msgid
            else:
                # Message creation failed.
                pass
        else:
            # Message suppressed from the UI; send to STDOUT only
            sys.stdout.write(text + '\n')

        return None
        
    def deleteMessage(self, namespace, owner, msgid, key):
        '''Deletes a UI message.
        
        @param uuid: The unique identifier for the message to delete.
        
        @return: True, False, or None indicating success/failure/nonexistent message ID, respectively.
        '''
    
        message = Message.get(Message.build_id(msgid, namespace, owner), sessionKey=key)
        return message.delete()
