from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField
import splunk.rest


class InputManager(SplunkAppObjModel):
    resource = 'configs/conf-inputs'
    disabled = BoolField()

    def enable(self, session_key):
        if not self.action_links:
            return True
        for item in self.action_links:
            if 'edit' in item:
                response, content = splunk.rest.simpleRequest(item[1], sessionKey=session_key, method='POST', postargs={'disabled': 0})
                if response.status == 200:
                    return True
        return False

    def disable(self, session_key):
        if not self.action_links:
            return True
        for item in self.action_links:
            if 'edit' in item:
                response, content = splunk.rest.simpleRequest(item[1], sessionKey=session_key, method='POST', postargs={'disabled': 1})
                if response.status == 200:
                    return True
        return False


def deployManagerInputs(session_key, logger, force=False):

    inputs = InputManager.search('name="threatlist_manager://*" OR name="identity_manager://*" OR name="dm_accel_settings://*"', sessionKey=session_key)

    enabled = 0
    total = 0
    found = 0
    for modinput in inputs:
        found += 1
        logger.info("Found the %s modular input", modinput.name)
        if force or modinput.disabled:
            total += 1
            if modinput.enable(session_key=session_key):
                enabled += 1
                logger.info("Enabled the %s modular input", modinput.name)
        else:
            logger.info("Skipping action for the %s modular input (may already be enabled)", modinput.name)

    logger.info("Enabled %s of %s total modular input stanzas (%s total found)", enabled, total, found)
    if enabled == total:
        return True
    else:
        return False
