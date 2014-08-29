'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import re

# convert decimal to binary with at least minDigits number of bits
def DecToBin(number, minBits = 8):

	bin = ''
	
	while number > 0:
		
		j = number & 1
		bin = str(j) + bin
		number >>= 1
	
	while len(bin) < minBits:
		bin = '0' + bin
	
	return bin

# convert dotted ip address to dotted binary
def IPToBin(ip):	

	ipDict = ip.split('.')
	index = 0
	binDict = { }
	
	for x in ipDict:
		
		binDict[index] = DecToBin(int(x))
		index += 1

	binIP = str(binDict[0]) + '.' + str(binDict[1]) + '.' + str(binDict[2])  + '.' + str(binDict[3])
	
	return binIP
	
# convert dotted binary to ip address
def BinToIP(binIP):

	binDict = binIP.split('.')
	index = 0
	ipDict = { }
	
	for x in binDict:
		
		ipDict[index] = int(x, 2)
		index += 1
	
	ip = str(ipDict[0]) + '.' + str(ipDict[1]) + '.' + str(ipDict[2]) + '.' + str(ipDict[3])
	
	return ip
	
# convert dotted ip address to long
def IPToLong(ip):
	
	ipDict = ip.split('.')
	long = 16777216*int(ipDict[0]) + 65536*int(ipDict[1]) + 256*int(ipDict[2]) + int(ipDict[3])
	return long
	
# convert long to dotted ip address
def LongToIP(long):
	
	ipDict = { }
	ipDict[0] = long / 16777216
	long = long - (ipDict[0] * 16777216)
	ipDict[1] = long / 65536
	long = long - (ipDict[1] * 65536)
	ipDict[2] = long / 256
	ipDict[3] = long - (ipDict[2] * 256)
	return str(ipDict[0]) + '.' + str(ipDict[1]) + '.' + str(ipDict[2]) + '.' + str(ipDict[3])
	
# convert dotted netmask to cidr
def NetmaskToCIDR(netmask):

	cidr = 0
	binNetmask = IPToBin(netmask)

	for x in binNetmask:
		if x == '1': 
			cidr += 1

	return cidr

# convert cidr to dotted netmask
def CIDRToNetmask(cidr):
	
	netmask = ''

	for x in range(0,cidr):
		netmask += '1'
	
	netmask += '00000000000000000000000000000000'
	netmask = netmask[0:32]
	
	return BinToIP(netmask[0:8] + '.' + netmask[8:16] + '.' + netmask[16:24] + '.' + netmask[24:32])
	
# convert dotted ip and netmask to ip range
def NetmaskToRange(ip, netmask):
	
	baseCIDR = 32
	ipRange = { }
	
	netmaskCIDR = NetmaskToCIDR(netmask)
	hostCount = pow(2, (baseCIDR - netmaskCIDR))

	
	binIP = IPToBin(ip)
	binNetmask = IPToBin(netmask)
	
	longIP = IPToLong(ip)
	
	startAddress = ""
	
	index = 0
	
	for x in binIP:
	
		if x != '.':
			startAddress = startAddress + str( int(x) & int(binNetmask[index]) )
		else:
			startAddress = startAddress + '.'
			
		index += 1
		
	ipRange['startAddress'] = BinToIP(startAddress)	
	ipRange['endAddress'] = LongToIP(IPToLong(ipRange['startAddress']) + hostCount - 1)
	
	return ipRange
	
def CIDRToRange(ipCIDR):

	parts = ipCIDR.split('/')
	if len(parts) == 2:
		baseIP = parts[0]
		subnet = CIDRToNetmask(int(parts[1]))
		ipRange = NetmaskToRange(baseIP, subnet)
		if ipRange:
			return ipRange
		
def convert_mac_to_long(value):
    
    if value is not None:
        new_value = value.replace('-', '')
        new_value = new_value.replace(':', '')
        if len(new_value) > 0:
                return long(new_value, 16)

def convert_long_to_mac(value):

    if value is not None:
        # 1 -- Get a hex version of the number
        basic_hex = hex(value)
        basic_hex = basic_hex.replace('0x', '')
        basic_hex = basic_hex.replace('L', '')
        basic_hex = basic_hex.zfill(12) # Add back the leading zeroes to ensure it is 12 characters long
        
        
        # 2 -- produce a string representing the MAC address with hex digits (uppercase) separated by colons

        #    2.1 -- Parse out the list of bytes
        regex = re.compile('([A-Fa-f0-9]{2,2})')
        match = regex.findall(basic_hex)
        
        final_string = None
        
        #    2.2 -- Append each byte to the final MAC address string
        if match is not None:
            for mac_byte in match:
                if final_string is None:
                    final_string = mac_byte.upper()
                else:
                    final_string =  final_string + ":" + mac_byte.upper() 
        
        return final_string
        
    else:
        return None