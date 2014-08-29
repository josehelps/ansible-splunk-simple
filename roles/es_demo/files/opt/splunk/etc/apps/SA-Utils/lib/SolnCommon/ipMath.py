'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import operator
import re


### Constants
# TODO: Move these constants into IPType class.
SUBNET_DELIM = '/'
RANGE_DELIM = '-'


### Conversion functions.
### Note that conversions should perform validation and return None
### in the event of failure.
def IPToLong(value):
    '''Convert dotted ip address to long.'''
    if is_valid_ip(value):
        ip = [int(x) for x in value.split('.')]
        return 16777216L * ip[0] + 65536 * ip[1] + 256 * ip[2] + ip[3]
    return None


def LongToIP(value):
    '''Convert long to dotted ip address.'''
    if isinstance(value, int):
        value = long(value)
    if isinstance(value, long):
        return '%d.%d.%d.%d' % ((value >> 24) % 256, (value >> 16) % 256, (value >> 8) % 256, value % 256)
    return None


def CIDRToLongTuple(value):
    '''Convert a CIDR subnet (checked for validity) to IP range expressed as two long integers.'''
    if is_valid_cidr(value):
        ip, subnet = value.split(SUBNET_DELIM)
        range_low = IPToLong(ip)
        hosts = pow(2, 32 - long(subnet)) - 1
        return (range_low, range_low + hosts)
    return None


### Validation functions
##
##  Validations should ALWAYS return a Boolean value,
##  or a value which can be validated as a Boolean,
##  such as a non-empty list. Exceptions should NOT be
##  raised.
def is_valid_mac(value):
    '''Validate a MAC address.'''
    rx = re.compile('^(([0-9A-Fa-f]{1,2}:){5}[0-9A-Fa-f]{1,2})$')
    try:
        return rx.match(value)
    except AttributeError:
        # Value was not a string
        return False


def is_valid_ip(value):
    '''Validate an IP address.'''
    rx = re.compile(r'''
    ^(((
          [0-1]\d{2}                  # matches 000-199
        | 2[0-4]\d                    # matches 200-249
        | 25[0-5]                     # matches 250-255
        | \d{1,2}                     # matches 0-9, 00-99
    )\.){3})                          # 3 of the preceding stanzas
    ([0-1]\d{2}|2[0-4]\d|25[0-5]|\d{1,2})$     # final octet
    ''', re.X)

    try:
        return rx.match(value)
    except (AttributeError, TypeError):
        # Value was not a string
        return False


def is_valid_mask(value):
    '''Validate a subnet mask.'''
    try:
        return int(value) >= 0 and int(value) <= 32
    except ValueError:
        return False


def is_valid_cidr(value, delim=SUBNET_DELIM):
    '''Validate a CIDR address.'''
    try:
        subnet, mask = value.split(delim, 1)
        if is_valid_ip(subnet) and is_valid_mask(mask):
            subnetLong = IPToLong(subnet)
            mask = int(mask)

            # Use floor division to get the number of valid bits that can
            # be specified in the subnet. For instance,
            # 1.1.1.1/24 is not valid; should be 1.1.1.0/24 
            invalidBits = pow(2, ((32 - mask) // 8) * 8) - 1
                
            return not subnetLong & invalidBits
    
    except (AttributeError, ValueError):
        # Not a string in CIDR format.
        return False


def expand_ip_range_to_cidr(rangeval, clean_single_ips=False, expand_subnets_smaller_than=None):
    '''
    Return a minimal list of CIDR addresses covering the same IPv4 range
    as the input range, inclusive. The input range MUST be one of the formats 
    shown below, representing a range a.b.c.d-e.f.g.h where a.b.c.d < e.f.g.h.
    If this is not true, ValueError will be raised.
    
    @param range: An IP address range in (<long> range_low, <long> range_high) format.
    @param clean_single_ips: If True, remove "/32" suffix from single IPs.
    @param expand_small_subnets: An integer between 24 and 31, representing the
        level at which a subnet will be expanded into a complete set of IP 
        addresses. If None, no expansion is performed.

    
    Output consists of a list of strings "a.b.c.d[/N]" where 0 <= N <= 32.
    '''
    
    # The output list of subnets.
    subnets = []
    
    RANGE_MIN = 0
    RANGE_MAX = pow(2, 32)
    
    rangeStartLong, rangeEndLong = rangeval
    
    if (rangeStartLong <= rangeEndLong
        and rangeStartLong >= RANGE_MIN and rangeEndLong >= RANGE_MIN 
        and rangeStartLong <= RANGE_MAX and rangeEndLong <= RANGE_MAX):

        # Begin range-to-CIDR algorithm.
        #
        # This algorithm is based on longest-common-prefix matching. Each subnet 
        # consists of a binary prefix of (32-N) digits, to which are appended
        # ALL binary integers up to N digits in length.
        #
        # 0. Convert rangeStart and rangeEnd to long integers (completed above). 
        # 1. Flip all of the 0 bits at the end of the binary representation
        #    of rangeStartLong to 1. The delta between rangeStartLong and 
        #    last_in_subnet will then represent a maximal block of IP
        #    addresses up to the next CIDR block. The next CIDR block will
        #    begin with a different prefix one bit shorter in length.
        # 2. If the last_in_subnet value is greater than the rangeEndLong value,
        #    our subnet is too large. Calculate the largest subnet (power of 2)
        #    that will fit into the range by using the bit_length() of the 
        #    difference between rangeStartLong and rangeEndLong, plus 1. This will
        #    give us the correct value of last_in_subnet.
        # 3. Emit the current subnet.
        # 4. Set rangeStartLong to the value of last_in_subnet plus 1, and repeat.
        # 5. Upon exiting the loop, rangeStartLong and rangeEndLong will exist
        #    in one of the following relations:
        #    a. rangeStartLong > rangeEndLong
        #       This means that the rangeEndLong matched our final subnet exactly,
        #       and no more coverage is needed.
        #    b. rangeStartLong == rangeEndLong
        #       This means that the subnet left one "dangling" IP, which should
        #       be covered via a /32 subnet.
        #
        # Example:
        #
        #    Given the following
        #
        #      rangeStart = 10.10.10.10, rangeEnd = 10.10.10.20
        #
        #    we have:
        #
        #      bin(rangeStartLong) = '0b1010000010100000101000001010'
        #      bin(rangeendLong)   = '0b1010000010100000101000010100'
        #
        #    This yields the following set of CIDRS covering the addresses
        #    shown in binary, with the common prefix marked by a pipe character:
        #
        #    10.10.10.10/31                 |
        #      '0b1010000010100000101000001010'    <- "0" suffix
        #      '0b1010000010100000101000001011'    <- "1" suffix
        #    10.10.10.12/30                |
        #      '0b1010000010100000101000001100'    <- "00" suffix
        #      '0b1010000010100000101000001101'    <- "01" suffix
        #      '0b1010000010100000101000001110'    <- "10" suffix
        #      '0b1010000010100000101000001111'    <- "11" suffix
        #    10.10.10.16/30              X |
        #      '0b1010000010100000101000010000'
        #      '0b1010000010100000101000010001'
        #      '0b1010000010100000101000010010'
        #      '0b1010000010100000101000010011'
        #    10.10.10.20/32                  |
        #      '0b1010000010100000101000010100'
        #
        #    Note that the subnet 10.10.10.16/30 would have been "reduced"
        #    from an originally calculated mask of /29. The "X" represents
        #    the original guess.
        
        while rangeStartLong < rangeEndLong:
            # Flip the rightmost zero bits; this will be our initial subnet guess.
            # See "Hacker's Delight" pg. 11.
            last_in_subnet = rangeStartLong | (rangeStartLong - 1)
            
            # Handle rollover when rangeStart is '0.0.0.0'
            if last_in_subnet == -1:
                last_in_subnet = 2 ** 32 - 1

            if last_in_subnet > rangeEndLong:
                # reduce to the largest possible size and retry
                diff = rangeEndLong - rangeStartLong + 1
                last_in_subnet = rangeStartLong + 2 ** (diff.bit_length() - 1) - 1

            mask = 32 - (last_in_subnet - rangeStartLong).bit_length()
            # For subnets in the expanded range that are smaller than /24, expand these
            # to their full complement of IP addresses if requested. Note that 
            # this includes x.x.x.0 and x.x.x.255 address, which mimics the
            # behavior of Splunk's "cidrmatch" eval comand.
            if expand_subnets_smaller_than and expand_subnets_smaller_than < 32 and expand_subnets_smaller_than >= 24:
                if mask >= expand_subnets_smaller_than:
                    for i in xrange(0, 2 ** (32 - mask)):
                        if clean_single_ips:
                            subnets.append(LongToIP(rangeStartLong + i))
                        else:
                            subnets.append(LongToIP(rangeStartLong + i) + '/32')
                else:
                    subnets.append('/'.join([LongToIP(rangeStartLong), str(mask)]))
            else:
                subnets.append('/'.join([LongToIP(rangeStartLong), str(mask)]))
            rangeStartLong = last_in_subnet + 1
        
        if rangeStartLong > rangeEndLong:
            pass
        elif rangeStartLong == rangeEndLong:
            # Add the last address
            if clean_single_ips:
                subnets.append(LongToIP(rangeStartLong))
            else:
                subnets.append(LongToIP(rangeStartLong) + '/32')
        else:
            # This should never happen due to the exit condition on the above while loop.
            raise ValueError("Subnet calculation failed unexpectedly.")

    else:
        # Invalid IP range.
        raise ValueError("Invalid IP range specified (perhaps reversed).")

    return subnets


def trim_cidr_list(cidr_list, mask):
    '''Given a list of subnets in CIDR format, trim any subnets that
    have a subnet value greater than or equal to the given mask. For instance given the
    parameters:
    
    cidrlist = [ '1.2.3.4/32', '1.2.3.4/31', '1.2.3.0/24' ]
    mask = 31

    this function would return
    
    new_list = [ '1.2.3.4', '1.2.3.4', '1.2.3.0/24' ]
    
    The most common use of this function is to return /32 CIDR subnets
    in string form.
    
    @param cidr_list: A list of IP subnets in CIDR format
    @param  mask: An integer between 0 and 32 inclusive.
    '''
    rv = []
    
    if mask < 0 or mask > 32:
        raise ValueError('Invalid mask value specified.')
    for cidr in cidr_list:
        if is_valid_cidr(cidr):
            ip, subnet = cidr.split('/')
            if int(subnet) >= mask:
                rv.append(ip)
            else:
                rv.append(cidr)
        else:
            raise ValueError('Value was not a valid CIDR subnet.')
    
    return rv


class IPType(object):
    '''Simple class for sanitizing IP address representations.'''
    
    # Enumeration of types.
    IPV4 = 0
    IPV6 = 1
    IPV4_RANGE = 2
    IPV6_RANGE = 3
    IP_INVALID = 4

    # Delimiters. This is intentionally not modifiable.    
    RANGE_DELIM = '-'
    SUBNET_DELIM = '/'
    
    # IP regex.
    IP_RX = re.compile(r'''
        ^(((
              [0-1]\d{2}                  # matches 000-199
            | 2[0-4]\d                    # matches 200-249
            | 25[0-5]                     # matches 250-255
            | \d{1,2}                     # matches 0-9, 00-99
        )\.){3})                          # 3 of the preceding stanzas
        ([0-1]\d{2}|2[0-4]\d|25[0-5]|\d{1,2})$     # final octet
    ''', re.X)
    
    @classmethod
    def is_valid_ip(cls, value):
        '''Validate an IP address.'''
        try:
            return cls.IP_RX.match(value)
        except (AttributeError, TypeError):
            # Value was not a string
            return False

    @classmethod
    def is_valid_ip_range_str(cls, low, high):
        '''Validate an IP address range in the format (a.b.c.d, e.f.g.h).'''
        try:
            return IPToLong(low) <= IPToLong(high) and cls.is_valid_ip(low) and cls.is_valid_ip(high)
        except (AttributeError, ValueError):
            pass
        return False
    
    @classmethod
    def is_valid_ipv4_integer_range(cls, low, high):
        '''Validate an IPv4 address range in the form (<int>, <int>).'''
        try:
            return 0 <= int(low) <= int(high) <= 4294967295
        except ValueError:
            pass
        return False

    @classmethod
    def get(cls, orig_value, force_range_repr=False):
        '''Return a canonical representation (repr, type) for the input 
        value.
        
        Arguments:
        value - a string or integer
        
        The representation will always be:
        repr - One of:
                - a valid IP address string 
                - a tuple of 2 integers in increasing order
                - the original value (must be accompanied by IP_INVALID)
        type - the type of the result
        '''

        ip_repr = None
        ip_type = None
        if isinstance(orig_value, basestring):
            value = orig_value.strip()
            
            if cls.is_valid_ip(value):
                if not force_range_repr:
                    return (value, IPType.IPV4)
                else:
                    tmp = IPToLong(value)
                    return ((tmp, tmp), IPType.IPV4_RANGE)

            # TODO: IPv6 support.
            #  elif is_valid_ipv6(value):
            #      return (value, IPType.IPV6_STR)
            
            elif SUBNET_DELIM in value:
                if is_valid_cidr(value, delim=SUBNET_DELIM):
                    ip, subnet = value.split(SUBNET_DELIM, 1)
                    range_low = IPToLong(ip)
                    hosts = pow(2, 32 - long(subnet)) - 1
                    ip_repr = (range_low, range_low + hosts)
                    ip_type = IPType.IPV4_RANGE
                else:
                    return (orig_value, IPType.IP_INVALID)
                
            elif RANGE_DELIM in value:
                low, high = value.split(RANGE_DELIM, 1)
                if cls.is_valid_ip_range_str(low, high):
                    ip_repr = [IPToLong(low), IPToLong(high)]
                    ip_type = IPType.IPV4_RANGE
                elif cls.is_valid_ipv4_integer_range(low, high):
                    ip_repr = [long(low), long(high)]
                    ip_type = IPType.IPV4_RANGE
                else:
                    return (orig_value, IPType.IP_INVALID)
                
        elif isinstance(orig_value, (int, long)):
            if 0 <= orig_value <= 4294967295:
                return (LongToIP(orig_value), IPType.IPV4)
            
            # TODO: IPv6 support.
            #elif 0 <= tmp <= 2**128 - 1:
            #    return (tmp, IPType.IPV6_INT)

            else:
                return (orig_value, IPType.IP_INVALID)

        # Convert to single IP if the range bounds are equivalent.
        if ip_repr[0] == ip_repr[1]:
            if not force_range_repr:
                return (LongToIP(ip_repr[0]), IPType.IPV4)
            else:
                return tuple([ip_repr, ip_type])
        elif ip_repr[0] < ip_repr[1]:
            return tuple([ip_repr, ip_type])
        elif ip_repr[0] > ip_repr[1]:
            return (orig_value, IPType.IP_INVALID)
        
    @classmethod
    def validate(cls, value):
        '''Validate an IP value.'''
        ip_repr, ip_type = cls.get(value)
        return ip_type != cls.IP_INVALID
