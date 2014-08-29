# b64.exiftool
# simple script that run exiftool on the decoded content.
import re
import json
import tempfile
import subprocess

def run(encoded_data, decoded_data, options = None):

	# write the content to a temporary named file
	f_tmp = tempfile.NamedTemporaryFile()
	f_tmp.write( decoded_data.read() )
	
	# analyze the temporary file with exiftool
	cmd = "exiftool -json -a -u -g1 %s" % f_tmp.name
	
	try:
		proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		p_out, p_err = proc.communicate()
	except Exception, e:
		return str(e)

	# destroy the tmp file
	f_tmp.close()

	# return exiftool output cleaned to avoid having an empty
	# starting node ('{}.NodeName') after using spath command.
	res = json.loads( p_out.strip() )
	str = json.dumps(res)
	str = re.sub("^\[", "", str)
	str = re.sub("\]$", "", str)

	return str
