import os
import sys
import shutil
import glob
import tarfile
import logging
from InstallUtil import InstallUtil
from SplunkCLI import SplunkCLI

class TAOssecUtil:
    #package = 'Splunk_TA_ossec'
    def __init__(self, splunk_home, logger):
        """
        Constructor of the TAOssecUtil object.
        """
        self.logger = logger
        self.splunk_home = splunk_home

    def get_and_install_ta_ossec(self):
        self.soln_root = os.environ["SOLN_ROOT"]
        self.logger.info("SOLN_ROOT:" + self.soln_root)
        if sys.platform.startswith("win"):
            # If we are on Windows
            install_util = InstallUtil("TA\\TA-ossec", self.splunk_home, self.logger)
        else:
            # If we are on Linux
            install_util = InstallUtil("TA/TA-ossec", self.splunk_home, self.logger)
        package = install_util.get_ta_solution()
        install_util.install_solution(package)
