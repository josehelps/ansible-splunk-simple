import py
import os
import sys
import time
import logging
import marshal
from TAOssecUtil import TAOssecUtil
from EventgenUtil import EventgenUtil
from ESSUtil import ESSUtil
from SplunkCLI import SplunkCLI
from SearchUtil import SearchUtil
from SplunkConf import SplunkConfManager
from install.deploy_windows_conf import deployWindowsConfFiles
from splunk import auth

class TestOssecKnowledge(object):

    logger = logging.getLogger('TestOssecKnowledge')
    
    def setup_class(self):
        self.logger.setLevel(logging.DEBUG)
        self.splunk_home = os.environ["SPLUNK_HOME"]
        self.logger.debug("SPLUNK_HOME:" + self.splunk_home)
        self.splunk_cli = SplunkCLI(self.splunk_home)
        self.logger.debug("Starting TA install")
        ossecutil = TAOssecUtil(self.splunk_home, self.logger)
        self.package1 = ossecutil.get_and_install_ta_ossec()

        self.logger.info("Getting ES Util")
        self.essutil = ESSUtil(self.splunk_home, self.logger)
        
        self.logger.info("Get and install eventgen")
        self.package2 = self.essutil.get_and_install_only_eventgen()
        if sys.platform.startswith("win"):
            deployWindowsConfFiles( os.path.join( self.splunk_home, "etc", "apps" ) )

        self.splunk_cli.restart()
        #wait until Splunk comes back
        time.sleep(10)
        
        self.logger.info("Getting Search Util")
        self.searchutil = SearchUtil(self.logger)
        self.eventgenutil = EventgenUtil(self.splunk_home, self.logger)
        self.logger.info("Start Eventgen")
        self.eventgenutil.run_eventgen()
    

        self.SplunkConfManager = SplunkConfManager(splunk_home=self.splunk_home)
         # enable eventgen
        settings = {
          "disabled" : "false"
        }

        if sys.platform.startswith("win"):
            # If we are on Windows then copy from this UNC path
            self.SplunkConfManager.updateLocalConf('inputs', "script://.\\bin\\eventgen.py", namespace='SA-Eventgen', **settings)
        else:
            # If we are on Linux then copy from this local path
            self.SplunkConfManager.updateLocalConf('inputs', "script://./bin/eventgen.py", namespace='SA-Eventgen', **settings)

        splunk_cmd_clean = 'clean all -f'
        self.splunk_cli.stop()
        self.splunk_cli.execute_command(splunk_cmd_clean)
        self.splunk_cli.start()

    def setup_method(self, method):
        self.logger.debug("In setup_method: doing nothing for now")    
        #nothing to do here
    
    '''
        This test requires an event like the following to be present in samples\sample.ossec
        Sep 18 04:02:10 acmescout1 ossec: Alert Level: 3; Rule: 5402 - Successful sudo to ROOT executed; Location: (acmescout3) 10.20.4.123->/var/log/auth.log; user: nagios;  Sep 18 04:02:09 acmescout3 sudo:   nagios : TTY=unknown ; PWD=/ ; USER=root ; COMMAND=/bin/su - cactidat -c ssh -o ConnectTimeout=2 192.168.91.24 sar -u 1 1
    '''
    
    
        
    def test_eventtype_ossec_attack(self):
        self.logger.debug("Testing eventtype ossec_attack.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCountIsGreaterThanZero(self.remote_key, "search eventtype=\"ossec_attack\"", '', 'search')
        assert result == True
    
    def test_eventtype_ossec_file_integrity_monitoring(self):
        self.logger.debug("Testing eventtype ossec_file_integrity_monitoring.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCountIsGreaterThanZero(self.remote_key, "search eventtype=\"ossec_file_integrity_monitoring\"", '', 'search')
        assert result == True
    
    def test_tag_ids(self):
        self.logger.debug("Testing tag ids.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCountIsGreaterThanZero(self.remote_key, "search eventtype=\"ossec_attack\" tag=\"ids\"", '', 'search')
        assert result == True
        
    def test_tag_attack(self):
        self.logger.debug("Testing tag attack.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCountIsGreaterThanZero(self.remote_key, "search eventtype=\"ossec_attack\" tag=\"attack\"", '', 'search')
        assert result == True
    
    def test_tag_endpoint(self):
        self.logger.debug("Testing tag endpoint.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCountIsGreaterThanZero(self.remote_key, "search eventtype=\"ossec_file_integrity_monitoring\" tag=\"endpoint\"", '', 'search')
        assert result == True
    
    def test_tag_change(self):
        self.logger.debug("Testing tag change.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCountIsGreaterThanZero(self.remote_key, "search eventtype=\"ossec_file_integrity_monitoring\" tag=\"change\"", '', 'search')
        assert result == True
    
    def test_signature_Multiple_Windows_audit_failure_events(self):
        self.logger.debug("Testing signature Multiple Windows audit failure events.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" signature=\"Multiple Windows audit failure events.\"", 6, '', 'search')
        assert result == True
    
    
    def test_signature_Integrity_checksum_changed_again_2nd_time(self):
        self.logger.debug("Testing signature Integrity checksum changed again (2nd time).")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" signature=\"Integrity checksum changed again (2nd time).\"", 2, '', 'search')
        assert result == True
    
    
    def test_signature_Windows_audit_failure_events(self):
        self.logger.debug("Testing signature Windows audit failure event.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" signature=\"Windows audit failure event.\"", 1, '', 'search')
        assert result == True
    
    def test_signature_Windows_error_event(self):
        self.logger.debug("Testing signature Windows error event.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" signature=\"Windows error event.\"", 1, '', 'search')
        assert result == True
         
    def test_intrusion_by_severity_medium(self):
        self.logger.debug("Testing severity medium.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" severity=\"medium\"", 6, '', 'search')
        assert result == True
    
    def test_intrusion_by_severity_low(self):
        self.logger.debug("Testing severity low")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" severity=\"low\"", 4, '', 'search')
        assert result == True
       
    def test_endpoint_changes_by_action_modified(self):
        self.logger.debug("Testing action modified.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" action=\"modified\"", 2, '', 'search')
        assert result == True
        
    def test_endpoint_changes_by_status_success(self):
        self.logger.debug("Testing status success.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" status=\"success\"", 2, '', 'search')
        assert result == True
        
    def test_endpoint_changes_by_change_type(self):
        self.logger.debug("Testing change_type filesystem.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" change_type=\"filesystem\"", 2, '', 'search')
        assert result == True
                    
    def test_endpoint_changes_by_file_name(self):
        self.logger.debug("Testing file_name.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" file_name=\"*\"", 2, '', 'search')
        assert result == True
        
    def test_endpoint_changes_by_object_category(self):
        self.logger.debug("Testing object_category field.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" object_category=\"*\"", 2, '', 'search')
        assert result == True
        
    def test_endpoint_changes_by_file_path(self):
        self.logger.debug("Testing file_path field.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" file_path=\"*\"", 2, '', 'search')
        assert result == True
        
    def test_endpoint_changes_by_file_hash(self):
        self.logger.debug("Testing file_hash field.")

        self.remote_key = auth.getSessionKey(username='admin', password='changeme', hostPath='')
        # run search
        result = self.searchutil.checkQueryCount(self.remote_key, "search sourcetype=\"ossec\" file_hash=\"*\"", 2, '', 'search')
        assert result == True
        
    def teardown_class(self):
        self.splunk_cli.stop()
        #os.remove(self.package1)
        #os.remove(self.package2)
