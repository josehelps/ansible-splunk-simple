# b64.shell
# run *any* shell command you like .. !
import re
import tempfile
import subprocess


"""
This module is deactivated by default. To activate it, comment the 
appropriate line in the beginning of the run() function.


Two magic words exist:
- encdata : represent the encoded data in base64
- decdata : represent the decoded data

To invoke them, use the notation <<>> like <<encdata>>.
Those magic words can be extended with the option ':ondisk'
to write the content on disk and the magic word will then 
be replaced by the filename of the file containing the data.

Examples:
# | b64 module=shell options="echo -ne <<encdata>> | wc -c"
# | b64 module=shell options="file <<decdata:ondisk>>"
# | b64 module=shell options="exiftool -json -a -u -g1 <<decdata:ondisk>>"
# | b64 module=shell options="cat /etc/password"

"""

def run(encoded_data, decoded_data, options):

	# comment the following line to activate this module
	return decoded_data.read()

	# substitute the magic words
	cmd = options
	cmd = re.sub('<<encdata>>', encoded_data.read(), cmd)
	cmd = re.sub('<<decdata>>', decoded_data.read(), cmd)

	f_enc = None
	f_dec = None

	if re.search('<<encdata:ondisk>>', cmd) :
		encoded_data.seek(0)
		f_enc = tempfile.NamedTemporaryFile()
		f_enc.write( encoded_data.read() )
		f_enc.flush()

		cmd = re.sub('<<encdata:ondisk>>', f_enc.name, cmd)

	if re.search('<<decdata:ondisk>>', cmd) :
		decoded_data.seek(0)
		f_dec = tempfile.NamedTemporaryFile()
		f_dec.write( decoded_data.read() )
		f_dec.flush()

		cmd = re.sub('<<decdata:ondisk>>', f_dec.name, cmd)
 
	# run the command 	
	try:
		proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		p_out, p_err = proc.communicate()
	except Exception, e:
		return str(e)

	# destroy the tmp files
	if f_enc != None :
		f_enc.close()
	if f_dec != None :
		f_dec.close()
	
	return p_out
