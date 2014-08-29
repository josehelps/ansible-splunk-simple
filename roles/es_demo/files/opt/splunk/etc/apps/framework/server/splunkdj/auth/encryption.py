import hashlib
import base64

try:
    from tlslite.utils import cipherfactory
    use_aes = True
except:
    use_aes = False

BLOCK_SIZE = 16

class _SimplerAES(object):
    def __init__(self, key):
        # First, generate a fixed-length key of 32 bytes (for AES-256)
        self._rawkey = key

    def pad(self, data):
        pad = BLOCK_SIZE - len(data) % BLOCK_SIZE
        return data + pad * chr(pad)

    def unpad(self, padded):
        pad = ord(padded[-1])
        return padded[:-pad]

    def encrypt(self, data):
        password = self._rawkey
        
        m = hashlib.sha1()
        m.update(password)
        key = m.hexdigest()[:32]

        m = hashlib.sha1()
        m.update(password + key)
        iv = m.hexdigest()

        data = self.pad(data)

        aes = cipherfactory.createAES(key, iv[:16])

        encrypted = str(aes.encrypt(data))
        
        return base64.urlsafe_b64encode(encrypted)

    def decrypt(self, edata):
        password = self._rawkey
        
        edata = base64.urlsafe_b64decode(str(edata))

        m = hashlib.sha1()
        m.update(password)
        key = m.hexdigest()[:32]

        m = hashlib.sha1()
        m.update(password + key)
        iv = m.hexdigest()

        aes = cipherfactory.createAES(key, iv[:16])
        return self.unpad(str(aes.decrypt(edata)))

class NoAES(object):
    def __init__(self, key):
        pass

    def pad(self, data):
        pass

    def unpad(self, padded):
        pass

    def encrypt(self, data):
        return base64.urlsafe_b64encode("%s:%s" % ("noaes", data))

    def decrypt(self, edata):
        edata = base64.urlsafe_b64decode(edata)
        return str(edata)[len("noaes:"):]

# Conditionally applies AES hashing depending on availability of the tlslite library.
SimplerAES = _SimplerAES if use_aes else NoAES

__all__ = ['SimplerAES']