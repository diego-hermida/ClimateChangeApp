# -*- coding: utf-8 -*-

"""
Copied from the implementation of `unittest-xml-reporting`.
There was an issue with the import of the test runner, which has been fixed here.
"""

import os
import xmlrunner.runner
import os.path
from django.conf import settings
from django.test.runner import DiscoverRunner


class XMLTestRunner(DiscoverRunner):
    # Changing xmlrunner.XMLTestRunner to xmlrunner.runner.XMLTestRunner FIXES this error.
    test_runner = xmlrunner.runner.XMLTestRunner

    def get_resultclass(self):
        # Django provides `DebugSQLTextTestResult` if `debug_sql` argument is True
        # To use `xmlrunner.result._XMLTestResult` we supress default behavior
        return None

    def get_test_runner_kwargs(self):
        # We use separate verbosity setting for our runner
        verbosity = getattr(settings, 'TEST_OUTPUT_VERBOSE', 1)
        if isinstance(verbosity, bool):
            verbosity = (1, 2)[verbosity]

        output_dir = getattr(settings, 'TEST_OUTPUT_DIR', '.')
        single_file = getattr(settings, 'TEST_OUTPUT_FILE_NAME', None)

        # For single file case we are able to create file here
        # But for multiple files case files will be created inside runner/results
        if single_file is None:  # output will be a path (folder)
            output = output_dir
        else:  # output will be a stream
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            file_path = os.path.join(output_dir, single_file)
            output = open(file_path, 'wb')

        return dict(
            verbosity=verbosity,
            descriptions=getattr(settings, 'TEST_OUTPUT_DESCRIPTIONS', False),
            failfast=self.failfast,
            resultclass=self.get_resultclass(),
            output=output,
        )

    def run_suite(self, suite, **kwargs):
        runner_kwargs = self.get_test_runner_kwargs()
        runner = self.test_runner(**runner_kwargs)
        results = runner.run(suite)
        if hasattr(runner_kwargs['output'], 'close'):
            runner_kwargs['output'].close()
        return results
