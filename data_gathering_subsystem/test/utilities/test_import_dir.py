from unittest import TestCase

import utilities.import_dir
from shutil import rmtree
from utilities.util import recursive_makedir


class TestImportDir(TestCase):

    def test_import_modules(self):

        recursive_makedir('./foo/bar/module_1')
        recursive_makedir('./foo/bar/module_2')
        recursive_makedir('./foo/bar/module_3')
        recursive_makedir('./foo/module_a')
        recursive_makedir('./foo/module_b')
        open('./foo/bar/module_1/__init__.py', 'w').close()
        open('./foo/bar/module_1/module_1.py', 'w').close()
        open('./foo/bar/module_2/__init__.py', 'w').close()
        open('./foo/bar/module_2/module_2.py', 'w').close()
        open('./foo/bar/module_3/__init__.py', 'w').close()
        open('./foo/bar/module_3/module_3.py', 'w').close()
        open('./foo/module_a/__init__.py', 'w').close()
        open('./foo/module_a/module_a.py', 'w').close()
        open('./foo/module_b/__init__.py', 'w').close()
        open('./foo/module_b/module_b.py', 'w').close()
        open('./foo/__init__.py', 'w').close()
        open('./foo/foo.py', 'w').close()

        # Case module names (with packages)
        expected = sorted(['foo.bar.module_1.module_1', 'foo.bar.module_2.module_2', 'foo.bar.module_3.module_3',
                    'foo.module_a.module_a', 'foo.module_b.module_b', 'foo.foo'])
        result = utilities.import_dir.get_module_names('./foo', recursive=True, base_package='foo')
        self.assertEqual(expected, result)

        # Case module names (only module names)
        expected = sorted(['module_1', 'module_2', 'module_3',
                           'module_a', 'module_b', 'foo'])
        result = utilities.import_dir.get_module_names('./foo', recursive=True, base_package='foo', only_names=True)
        self.assertEqual(expected, result)

        # Case paths
        expected = sorted(['./foo/bar/module_1/module_1', './foo/bar/module_2/module_2', './foo/bar/module_3/module_3',
                           './foo/module_a/module_a', './foo/module_b/module_b', './foo/foo'])
        result = utilities.import_dir.get_module_paths('./foo', recursive=True, base_package='foo')
        self.assertEqual(expected, result)

        # Case modules
        result = utilities.import_dir.import_modules('./foo', recursive=True, base_package='foo')
        self.assertEqual(len(expected), len(result))

        rmtree('./foo')
