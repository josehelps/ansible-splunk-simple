#############################################
# 
# simple framework for base64 decoding
# 
# - Consider using the dedup command _before_ calling this script.
# - Adjust the maxinputs parameter in commands.conf to fit your env.
# 
#############################################
import splunk.Intersplunk
import re
import sys
import tempfile
import base64

##########
# CONFIG #
##########

# The maximum size of content stored in memory. Files greather than that size
# will be written to disk. The b64 command is mono-thread so large sizes are 
# ok (if you have enough memory!)
# 
# The required memory is actually twice this value as we store in memory the 
# encoded and the decoded form of the data.
# 
# default: 32 MB
IN_MEMORY_MAX_FILESIZE = 32 * 1024 * 1024


########
# MAIN #
########
# | b64 [field=pouet] module=decode [options="free form quoted string"]
# | b64 [field=pouet] module=shell options="ls -lh"
# | b64 [field=pouet] module=mymodule options="myopt1=true myopt2=bonjour"

# default values
args = {
	'module'  : None,
	'options' : None,
	'field'   : "extraction_file"
}

# we assume the users use key="value" (no whitespace) and not 
# key = "value" or key= "value" or key ="value"
for item in sys.argv[1:]:
	if re.search('^=|=$', item) :
		splunk.Intersplunk.parseError("use key=\"value\" and not key = \"value\" (no whitespace allowed between key/value)")

	reg_t = re.search("(\w+)=([^$]+)", item)
	
	if reg_t :
		k = reg_t.group(1)
		v = reg_t.group(2)
		args[ k ] = v
	else:
		splunk.Intersplunk.parseError("Unrecognized argument: %s" % str(item))

if args['module'] == None :
	splunk.Intersplunk.parseError("You must provide a module to use (module=<string>).")

# read inputs from stdin
results  = splunk.Intersplunk.readResults(None, None, True)

for r in results:

	# get a row
	try:
		data_base64 = r[ args['field'] ].strip()
		if( data_base64 == "-" or data_base64 == "" ):
			continue
	except:
		splunk.Intersplunk.parseError("Wrong field name: \"%s\"" % args['field'] )

	# create 2 streams: 1 for the encoded data and another for the decoded data.
	encoded_data = tempfile.SpooledTemporaryFile(max_size=IN_MEMORY_MAX_FILESIZE)
	encoded_data.write( data_base64 )

	decoded_data = tempfile.SpooledTemporaryFile(max_size=IN_MEMORY_MAX_FILESIZE)
	try:
		encoded_data.seek(0)
		base64.decode(encoded_data, decoded_data)
	except Exception, e:
		splunk.Intersplunk.parseError("Python base64 decoding error: %s" % str(e))

	encoded_data.seek(0)
	decoded_data.seek(0)

	# execute the provided module
	try:
		mod = __import__("b64.%s" % args['module'], fromlist = [ args['module'] ])
		r["b64_result"] = mod.run(encoded_data, decoded_data, args['options'] )
	except Exception, e:
		splunk.Intersplunk.parseError(str(e))

	# destroy the streams
	encoded_data.close()
	decoded_data.close()

splunk.Intersplunk.outputResults(results)

