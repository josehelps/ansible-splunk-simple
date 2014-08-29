#!/usr/bin/env python
import os
import re
import sys
import time
import base64
import pickle
import errno
import logging
import shutil
import os.path
import tempfile
import threading
import subprocess

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from logging import handlers
from hashlib import md5
from signal import SIGTERM, SIGKILL

#TODO: Handle the case where db/local_pcap.dat.lock exist whithout db/local_pcap.dat 


def setup_logger(name = None):
	if name is None:
		name = os.path.splitext(__file__)[0]

	logger = logging.getLogger(name)
	logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
	logger.setLevel(logging.INFO)

	file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', name + '.log']), maxBytes=25000000, backupCount=5)
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	file_handler.setFormatter(formatter)

	logger.addHandler(file_handler)
	return logger
logger = setup_logger("Splunk_TA_bro")



class run_command(object):

	def __init__(self, cmd, timeout = None):
		self.cmd = cmd
		self.timeout= timeout
		self.process = None
		self.std_out = None
		self.std_err = None
		self.exception = None

	def _run(self):
		try:
			self.process = subprocess.Popen( self.cmd,
				shell  = True,
				stdin  = subprocess.PIPE,
				stdout = subprocess.PIPE,
				stderr = subprocess.PIPE,
			)
			out, err = self.process.communicate()

			if err.strip() != "" :
				self.std_err = err

			if out.strip() != "" :
				self.std_out = out

		except Exception, e:
			self.exception = e
	# eof _run()

	def run(self):

		t = threading.Thread(target=self._run)
		t.start()
		t.join(self.timeout)

		if self.exception :
			return None, self.exception
        
		if t.is_alive() :
			os.kill(self.process.pid, SIGTERM)
			self.std_err = "maximum time reached, SIGTERM sent."
			t.join(5) # wait 5 seconds more to thread finish

		if t.is_alive() :
			os.kill(self.process.pid, SIGKILL)
			self.std_err = "maximum time reached, SIGKILL sent."
			t.join()

		self.returncode = self.process.returncode
		return self.std_out, self.std_err
	# eof run()

# eof class run_command



from modular_input import Field, FieldValidationException, ModularInput, BooleanField

class PcapMonitorModularInput(ModularInput):
	"""
	This modular inputs watch for new pcaps in directories to process them using Bro.
	By default, only pcaps metadata are extracted but content can also be extracted using
	Bro scripts and this content is then encoded in Base64 to be ingested by Splunk.
	"""

	def __init__(self, timeout=30):
		scheme_args = {
			'title': "PCAP",
			'description': "Watch directories for packet capture files (*.pcap) and process them using Bro."
		}

		args = [
			Field("path", "Path", 
				"Specify where the pcap files are stored (eg: /var/pcap).", empty_allowed=False),
			BooleanField("recursive", "Recursive", 
				"Specify if splunk should monitor all sub directories for incoming pcap. True or False.", empty_allowed=False),
			Field("store_dir", "Log directory",
				"Specify where the created log files by Bro will be stored (eg: /var/log/bro).", empty_allowed=False),
			Field("bro_bin", "Bro binary", 
				"Specify where the Bro binary is located (eg: /opt/bro/bin/bro).", empty_allowed=False),
			Field("bro_opts", "Bro options", 
				"Specify options to pass to Bro (None to deactivate).", empty_allowed=False),
			Field("bro_script", "Bro script",
				"Specify a Bro script to use or None do deactivate.", empty_allowed=False),
			Field("bro_seeds", "Bro seed file",
				"Specify if you want to use a seed file to predict Bro UIDs or None do deactivate.", empty_allowed=False),
			BooleanField("bro_merge", "Ingest content",
				"[Bro 2.1 only] Specify if the extracted content by Bro must be encoded in Base64 and appended to Bro logs. This require a Bro script to be set and this is a True or False option.", empty_allowed=False),
			Field("content_maxsize", "Content maximum size",
				"[Bro 2.1 only] Objects greather than the specified size (in bytes) will not be ingested.", empty_allowed=False),
			Field("run_maxtime", "Maximum execution time",
				"When a Bro instance run longer than this time (in secs), kill the instance. Set to 0 to deactivate.", empty_allowed=False),
		]

		ModularInput.__init__( self, scheme_args, args )
	# eof __init__()

	def set_envvars(self, var):
		items = var.split(os.sep)
		for x in xrange(0,len(items)):
			if items[x] == '$SPLUNK_HOME' :
				items[x] = make_splunkhome_path([''])
			elif items[x].startswith('$') :
				envvar     = items[x].lstrip('$')
    				envvar_val = ""
				try:
					envvar_val = os.environ[envvar]
				except KeyError:
					logger.error("%s could not be found in os environment variables" % envvar)
					#raise admin.ArgValidationException("%s could not be found in os environment variables" % envvar)
				items[x] = os.path.normpath(envvar_val)
		return os.sep.join(items)

	#r = getPcapFiles("/var/pcap", True)
	def getPcapFiles(self, path, recurse = False):
		"""
		Return the list of files contained in path and with extension .pcap or .cap
		Return also files in sub directories if recurse is set to True.
		Each item has 3 attributes: file, b64(file) and size in bytes.
		"""
		pList = []
	
		if( recurse ):
			for root, dirs, files in os.walk(path):
				for f in files:
					f_pcap = os.path.join(root, f)
					if( re.search("\.p?cap$", f) and os.path.isfile(f_pcap) ):
						pList.append(f_pcap)
		else:
			for f in os.listdir(path):
				f_pcap = os.path.join(path, f)
				if( re.search("\.p?cap$", f) and os.path.isfile(f_pcap) ):
					pList.append(f_pcap)
	
		pList = sorted(pList)

		ret = {}
		for f in pList:
			ret[ base64.b64encode(f) ] = {'file': f, 'size': os.stat(f).st_size, 'nChecks':0}
		return ret
	# eof getPcapFiles()

	# A pcap a 3 status:
	# - copied - parsed
	# - copied - not parsed
	# - being copied - not parsed
	#r = getPcapToParse("myStore", "/var/pcap/", "/opt/splunk/var/.../checkpoint_dir", False)
	def getPcapToParse(self, stanza, path, checkpoint_dir, recurse=False):
		"""
		Return a list of pcaps that can be parsed. A pcap is considered ready to be
		parsed when its size didn't change between two checks.
		In case of a filesize change on an already parsed pcap, then the pcap is 
		considered as a new one and will be parsed again.

		As a first step, try to acquire a lock on the related db. If its not possible,
		log an error and return an empty list (assuming a previous Bro instance is still
		running). This is a non-blocking behavior to avoid multiple scripts instances 
		queued.
		"""
		# history file  -- keep a record of known pcaps and associated size
		# /path/to/checkpoint_dir/md5(stanza).dat (stanza are supposed to be unique)
		f_repo       = md5(stanza).hexdigest() + '.dat'
		history_file = os.path.normpath( os.path.join(checkpoint_dir, f_repo) )

		# lock the history file
		lock_file = "%s.lock" % history_file
		if( os.path.isfile(lock_file) ):
			logger.warning("Can't acquire lock on %s -- Previously Bro instance still running?" % history_file)
			return []
		open(lock_file,"w").write("1")

		# load known pcap file list
		knownPcapFiles = {}
		try:
			f = open(history_file, "rb")
			knownPcapFiles = pickle.load(f)
			f.close()
		except EOFError:
			# Ignore empty pickle
			pass
		except IOError as e:
			# Ignore "no such file or directory" errors
			if ( e.errno == 2 ):
				pass
			else:
				logger.error(str(e))
				raise e

		pcapToParse= []
		pcapOnDisk = self.getPcapFiles(path, recurse)
		for b64file in pcapOnDisk:

			# The filename is not known, its a new file, just add it the "db"
			if( not (b64file in knownPcapFiles) ):
				knownPcapFiles[ b64file ] = pcapOnDisk[b64file]
				continue

			# The file is known, several senarios
			# same size since the last check, the file did not changed (this should be suffisant check).
			# new file: add in db
			# new file with same size as previous check, inc by 1 nCheck
			# new file with 2 times the same size: parse-it
			# if a known/already parsed pcap has his size changing, it will be parsed again.
			if( knownPcapFiles[ b64file ]['size'] == pcapOnDisk[ b64file ]['size'] ):
				knownPcapFiles[ b64file ]['nChecks'] += 1
			
				if( knownPcapFiles[ b64file ]['nChecks'] == 2 ):
					pcapToParse.append( knownPcapFiles[ b64file ]['file'] )
				elif( knownPcapFiles[ b64file ]['nChecks'] > 2 ):
					knownPcapFiles[ b64file ]['nChecks'] = 3 # avoid infinite growth
			else:
				knownPcapFiles[ b64file ]['nChecks'] = 0
				knownPcapFiles[ b64file ]['size']    = pcapOnDisk[ b64file ]['size']

		f = open(history_file, "wb")
		pickle.dump(knownPcapFiles, f)
		f.close()

		os.remove(lock_file)

		return pcapToParse
	# eof getPcapToParse()



	def mergeDataAndStreams(self, max_payload_size):
		"""
		/!\ This function is very dependant of the version of Bro you are using.
		/!\ This function has been coded with Bro 2.1 only
		/!\ This will not work properly with Bro 2.2 as the whole extraction
		/!\ engine has been rewrote.

		If a script was provided to Bro, the data/payloads have been extracted
		to .dat files. This functions encode this data in Base64 and merge it
		in the flow log file, replacing the column "extraction_file" which by
		default point the name of the .dat file.
	
		Files greather than max_payload_size bytes will not be base64 encoded 
		and included in the logs files.

		The merge will only be done for files declared in bro_modules array.

		Ex: http.log refer files like http-item_192.168.204.70:58473-192.168.202.78:80_resp_1.dat        
		"""
		# files => file_extraction regex pattern
		bro_modules = {
			"ftp.log" :"(ftp-item_\S+)",
			"http.log":"(http-item_\S+)",
			"irc.log" :"(irc-item_\S+)",
			"smtp_entities.log": "(smtp-entity_\S+)",
		}

   
		# list all .dat files and their size
		datFiles = {}
		Files    = [f for f in os.listdir('.') if os.path.isfile(f)]
        
		for f in Files:
			if( re.search("\.dat$", f) ):
				datFiles[ f ] = os.stat(f).st_size

		if( len(datFiles) == 0 ):
			return

		# For each log, rewrite it by including dat files except if they are too large
		for mod_file in bro_modules:
			mod_regex = bro_modules[ mod_file ]

			# Just try to open the log and if it fail, jump to the next one
			try:
				f = open(mod_file, "r")
			except:
				continue

			# Open the temporary output file (ex: http.log.rw)
			dst_file = "%s.rw" % mod_file
			try:
				f_out = open(dst_file, "w")
			except Exception, e:
				raise e

			# Read each line into the log file and substitute the payload filename by its base64 value
			line = f.readline()
			while line:
				line = line.strip()
				r = re.search(mod_regex, line)

				# no payload / dat file
				if( not r ):
					f_out.write(line + '\n')
					line = f.readline()
					continue

				payload_filename = r.group(1) #http-item_192.168.204.70:58473-192.168.202.78:80_resp_1.dat

				# File is too big, discard it.
				datSize = datFiles[payload_filename]
				if( datSize > max_payload_size ):
					logger.info("Discarded file %s due to file size limitation (%s bytes)" % (payload_filename, datSize))
					f_out.write(line + '\n')
					line = f.readline()
					continue

				# we consider that the payload always fit in memory
				payload = ""
				try:
					payload = base64.b64encode(open(payload_filename, 'rb').read())
				except Exception, e:
					raise e

				line = re.sub(payload_filename, payload, line)
				f_out.write(line +'\n')
				line = f.readline()
			# end while

			f.close()
			f_out.close()

			# mv http.log.rw http.log
			shutil.move(dst_file, mod_file)
		# end of for
	# eof mergeDataAndStreams()


	def moveLogs(self, store_dir, stanza_name, pcap_file, merge_content, max_content_size):
		"""
		Write log in output directories with the following pattern:
		/specified/output/dir/md5(stanza_name)/md5(pcap_file).bro.conn.log

		A pcap is supposed to be parsed only once (per stanza)
		
		Ex: conn.log become <md5>.bro.conn.log
		"""
		md5_stanza = md5( stanza_name ).hexdigest()
		md5_pcap   = md5( pcap_file   ).hexdigest()

		o_dir = os.path.normpath( os.path.join(store_dir, md5_stanza) )
		o_file_base = os.path.normpath( os.path.join(o_dir, md5_pcap) )

		# create the storage directories if required
		try:
			os.makedirs( o_dir )
		except Exception, e:
			if( e.errno != errno.EEXIST ):
				logger.error(str(e))
				raise e

		# merge extracted content if required
		if( merge_content ):
			self.mergeDataAndStreams(max_content_size)

		# move remaining log files
		files = [file for file in os.listdir('.') if os.path.isfile(file)]

		for file in files:
			if( not re.search("\.log$", file) ):
				continue

			o_file = "%s.bro.%s" % (o_file_base, file) # md5(pcap_file).conn.log
			shutil.move(file, o_file)
	# eof moveLogs()

	def parseNewPcap(self, stz, params, config): 
		"""
		Get a list of new pcaps and parse them using Bro
		"""
		index      = params['index']
		pcap_path  = params['path']
		recursive  = params['recursive']
		bro_bin    = params['bro_bin']
		bro_opts   = params['bro_opts']
		bro_script = params['bro_script']
		bro_seeds  = params['bro_seeds']
		store_dir  = params['store_dir']

		max_execution_time = int(params['run_maxtime'])
		merge_content      = int(params['bro_merge'])
		max_content_size   = int(params['content_maxsize'])
		checkpoint_dir     = config['checkpoint_dir']

		# simple args check
		if (max_execution_time <= 0):
			max_execution_time = None
		if (merge_content != 1):
			merge_content = 0
		if (max_content_size <= 0):
			merge_content = 0
			params['bro_merge'] = 0
			max_content_size = 0	

		# Get a list of new pcaps ready to be parsed
		pcapToParse = self.getPcapToParse(stz['name'], pcap_path, checkpoint_dir, recursive)

		if( len(pcapToParse) == 0 ):
			logger.info("no pcap to parse found (%s)." % stz['name'])
			return 0

		# parse each pcaps
		for pcap_file in pcapToParse:
			start_time = time.time()
			logger.info("Parsing %s" % pcap_file)

			# work in a temporary directory
			current_dir = os.getcwd()
			tmp_dir = tempfile.mkdtemp(prefix="splunk-bro-")
			os.chdir(tmp_dir)

			# build the Bro command
			cmd = ""
			if( os.path.isfile(bro_seeds) ):
				cmd =  "export BRO_SEED_FILE=%s && " % bro_seeds
			if( (bro_opts == None) or (bro_opts == "None") ):
				bro_opts = ""

			cmd += "%s %s -r %s" % (bro_bin, bro_opts, pcap_file)

			if( os.path.isfile(bro_script) ):
				cmd += " %s " % bro_script

			# run Bro !
			logger.info("running command = %s" % cmd)
			out, err = run_command(cmd, timeout=max_execution_time).run()
		
			if err != None :
				status = 'bro_ran_with_failures'
				logger.error("something went wrond during Bro execution: %s" % err)
			else:
				status = 'bro_ran_successfully'
				# Bro should have output'ed a lot of files merge & move them
				self.moveLogs(store_dir, stz['name'], pcap_file, merge_content, max_content_size)

			# remove tmp working dir
			os.chdir(current_dir)
			shutil.rmtree(tmp_dir, ignore_errors = True)

			end_time = time.time()

			# output event
			o_evt = {
				'pcap'      : pcap_file,
				'md5_pcap'  : md5( pcap_file  ).hexdigest(), 
				'stanza'    : re.sub('\s+', '_', stz['name']),
				'md5_stanza': md5( stz['name']).hexdigest(),
				'store_dir' : store_dir,
				'start_time': start_time,
				'end_time'  : end_time,
				'bro_exec'  : re.sub('\s+', '_', status)
			}
			self.output_event(o_evt, stz['stanza'], index)
	# eof parseNewPcap() 

	def run(self, stanza, cleaned_params, input_config):
		# 'sanitize' the stanza to just get the name the user gave
		# pcap_monitor://<name>
		stz = {
		'stanza' : stanza,
		'name'   : re.sub('^pcap_monitor://', '', stanza)
		}
		logger.info("Pcap Monitor(%s)" % stz['name'])

		# Get the path to monitor
		cleaned_params["path"]      = self.set_envvars(cleaned_params["path"])
		cleaned_params["bro_bin"]   = self.set_envvars(cleaned_params["bro_bin"])
		cleaned_params["store_dir"] = self.set_envvars(cleaned_params["store_dir"])
	
		if( not os.access(cleaned_params["path"], os.F_OK | os.R_OK) ):
			logger.error("Can't access to pcap directory (%s)" % cleaned_params["path"])
			sys.exit(-1)

		if( not os.access(cleaned_params["bro_bin"], os.F_OK | os.X_OK) ):
			logger.error("Can't access to bro binary (%s)" % cleaned_params["bro_bin"])
			sys.exit(-1)

		if( not os.access(cleaned_params["store_dir"], os.F_OK | os.W_OK) ):
			logger.error("Can't access to store_dir (%s)" % cleaned_params["store_dir"])
			sys.exit(-1)

		self.parseNewPcap(stz, cleaned_params, input_config) 
	# eof run()

# eof class PcapMonitorModularInput


if __name__ == '__main__':
	try:
		pcap_monitor_modular_input = PcapMonitorModularInput()
		pcap_monitor_modular_input.execute()
		sys.exit(0)
	except Exception as e:
		# This logs general exceptions that would have been unhandled otherwise (such as coding errors)
		logger.exception("Unhandled exception was caught, this may be due to a defect in the script") 
		raise e

