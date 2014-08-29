'''
Copyright (C) 2009-2012 Splunk Inc. All Rights Reserved.
'''
import csv
import os
import re
import sys

# set the maximum allowable CSV field size 
# 
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for 
# the background on issues surrounding field sizes. 
# (this method is new in python 2.5) 
csv.field_size_limit(10485760)

## This Python function implements the algorithm described above, returning True if the given input 
## represents a valid Luhn number, and False otherwise. It expects the input as (1) a string of 
## digits, or (2) an array of digits, each of which must be an integer 0<=n<=9. It reverses the 
## digits, and it uses a boolean alternator.
def check_number(digits):
	_sum = 0
	alt = False
	
	for d in reversed(digits):
		d = int(d)
		assert 0 <= d <= 9
		if alt:
			d *= 2
			if d > 9:
				d -= 9
		_sum += d
		alt = not alt
	return (_sum % 10) == 0
	
def encodeCR(result):
	result = result.replace('\r','!splunk\\0Dsplunk!')
	return result

def decodeCR(result):
	result = result.replace('!splunk\\0Dsplunk!','\r')
	return result
  
    
if __name__ == '__main__':
	
	## Defaults
	separators = "\s -"
	minStrength = 10
	maxStrength = 19
	offset = 0
		
	## Override Defaults w/ opts below
	if len(sys.argv) > 1:
		for a in sys.argv:
			if a.startswith("separators="):
				where = a.find('=')
				separators = a[where+1:len(a)]
			elif a.startswith("minStrength="):
				where = a.find('=')
				minStrength = a[where+1:len(a)]
			elif a.startswith("maxStrength="):
				where = a.find('=')
				maxStrength = a[where+1:len(a)]
			elif a.startswith("offset="):
				where = a.find('=')
				offset = a[where+1:len(a)]
		
	## Create list of digit separators
	separators = separators.strip()
	separators = separators.split(' ')
		
	## Typing
	minStrength = int(minStrength)
	maxStrength = int(maxStrength)
	offset = int(offset)
		
	## Timestamp pattern list
	timestampPatternList = []
	timestampPatternList.append('\w{3}\s+\d{1,2}\,?\s+\d{2}\:\d{2}\:\d{2}(\s+\d{4})?')
	timestampPatternList.append('\d{2}\-\d{2}\-\d{4}\s+\d{2}\:\d{2}\:\d{2}')
		
	## Initialize pattern list
	digitsPatternList = []
 	
	## Generate patterns
	for separator in separators:
		digitsPatternList.append('((\d+([' + separator + ']+)?){' + str(minStrength) + ',})')

	header = []
	first = True   
	outputResults = []
 
	newstdin = os.tmpfile()
	for result in sys.stdin:
		result = encodeCR(result)
		newstdin.write(result)
	newstdin.seek(0)

	inputResults = csv.reader(newstdin, lineterminator='\n')
		
	for inputResult in inputResults:

		digitsList = []
		outputResult = {}
			
		if first:
			header = inputResult
			csv.writer(sys.stdout, lineterminator='\n').writerow(header)
			outputResults = csv.DictWriter(sys.stdout, header, lineterminator='\n')
			outputResultsQA = csv.DictWriter(sys.stdout, header, quoting=csv.QUOTE_ALL, lineterminator='\n')
			first = False
				
		else:
			outputResult = {}
			forwardLookup = False
			
			for x in range(0,len(inputResult)):
				outputResult[header[x]] = decodeCR(inputResult[x])
		
			if outputResult.has_key(header[0]) and len(outputResult[header[0]]) > 0:
				forwardLookup = True
					
				if len(outputResult[header[0]]) > offset:
					val = outputResult[header[0]][offset:len(outputResult[header[0]])]
							
				else:
					val = outputResult[header[0]]
					
				for pattern in digitsPatternList:
					for timestampPattern in timestampPatternList:
						val = re.sub(timestampPattern, '', val)
						digitsList.extend(re.findall(pattern,val))
												
				for digits in digitsList:
					origdigits = digits[0]
					digits = re.sub('[^0-9]', '', digits[0])
					digits = re.sub('[0]{' + str(len(digits)) + '}', '', digits)
							
					if len(digits) > 0 and len(digits) <= maxStrength:
						if check_number(digits):
							outputResult[header[1]] = origdigits
							outputResult[header[2]] = digits
							break
			
			if forwardLookup:
				outputResults.writerow(outputResult)
				
			else:
				outputResultsQA.writerow(outputResult)
			
	newstdin.close()