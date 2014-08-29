import logging
import os
from BuildUtil import BuildUtil


class TestBuildTAossec:
    logger = logging.getLogger('ta_ossec-build')

    # in this method we just build TA-ossec
    def test_build(self):
        codeline = os.environ["CODELINE"]
        buildutil = BuildUtil('TA/TA-ossec', codeline, 'tgz', self.logger)
        buildutil.build_solution()