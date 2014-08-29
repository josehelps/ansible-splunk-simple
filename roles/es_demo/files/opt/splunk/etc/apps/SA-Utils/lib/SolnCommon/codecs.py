'''
Copyright (C) 2005 - 2013 Splunk Inc. All Rights Reserved.
'''
import gzip
import StringIO
import struct
import zipfile


class GzipHandler(object):
    '''Class for handling gzip-formatted string content.'''

    # Error messages
    ERR_INVALID_FORMAT = 'File is not gzip format.'
    ERR_SIZE_MISMATCH = 'Gzip file size does not match actual.'

    def __init__(self):
        pass

    @classmethod
    def checkFormat(cls, data):
        '''Take a string and validate whether it is in gzip
           format. 
        '''
        # Check for gzip header.
        # Bytes 0 and 1 should be (per RFC 1952):
        # ID1 = 31 (0x1f, \037), ID2 = 139 (0x8b, \213)
        return data[0:2] == '\037\213'

    @classmethod
    def decompress(cls, data):
        '''Decompress a string containing gzip-compressed data,
           performing basic validation. Returns the decompressed
           data or raises ValueError with an error string.
        '''

        # 1 - Check format.
        if not cls.checkFormat(data):
            raise ValueError(cls.ERR_INVALID_FORMAT)

        # 2 -- Read length of file from last four bytes of data.
        # This should be the size of the uncompressed data mod 2^32
        # Note that unpack() always returns a tuple even for one item
        sizeInt, = struct.unpack('i', data[-4:])

        # 3 -- Decompress the string
        decompressor = gzip.GzipFile(fileobj=StringIO.StringIO(data), mode='rb')
        text = decompressor.read()

        # 4 -- Check decompressed size.
        if len(text) != sizeInt:
            raise ValueError(cls.ERR_SIZE_MISMATCH)

        return text


class ZipHandler(object):
    '''Class for handling zip files.'''

    # Error messages
    ERR_EXCESS_FILES = 'Zip files containing multiple files not supported by this handler.'
    ERR_EXTRACT_ERROR = 'Unknown exception when extracting zip file.'
    ERR_INVALID_FORMAT = 'File is not zip format.'
    ERR_SIZE_MISMATCH = 'Zip file size does not match actual size.'

    def __init__(self):
        pass

    @classmethod
    def checkFormat(cls, data):
        '''Take a string and validate whether it is in zip
           format. 
        '''
        return zipfile.is_zipfile(StringIO.StringIO(data))

    @classmethod
    def decompress(cls, data):
        '''Decompress a string containing zip-compressed data,
           performing basic validation. Returns the decompressed
           data or raises ValueError with an error string.
        '''

        if not cls.checkFormat(data):
            raise ValueError(cls.ERR_INVALID_FORMAT)

        fh = StringIO.StringIO(data)
        decompressor = zipfile.ZipFile(fh)

        files = decompressor.infolist()
        if len(files) > 1:
            raise ValueError(cls.ERR_EXCESS_FILES)
        else:
            try:
                text = decompressor.read(files[0].filename)
            except:
                raise ValueError(cls.ERR_EXTRACT_ERROR)

        if len(text) != files[0].file_size:
            raise ValueError(cls.ERR_SIZE_MISMATCH)

        return text
