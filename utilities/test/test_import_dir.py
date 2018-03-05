from unittest import TestCase

import utilities.import_dir
from shutil import rmtree
from utilities.util import recursive_makedir


class TestImportDir(TestCase):

    @classmethod
    def setUpClass(cls):
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

    @classmethod
    def tearDownClass(cls):
        rmtree('./foo')

    def test_import_modules_with_paths(self):
        expected = sorted(['foo.bar.module_1.module_1', 'foo.bar.module_2.module_2', 'foo.bar.module_3.module_3',
                    'foo.module_a.module_a', 'foo.module_b.module_b', 'foo.foo'])
        result = utilities.import_dir.get_module_names('./foo', recursive=True, base_package='foo')
        self.assertEqual(expected, result)

    def test_import_modules_only_names(self):
        expected = sorted(['module_1', 'module_2', 'module_3',
                           'module_a', 'module_b', 'foo'])
        result = utilities.import_dir.get_module_names('./foo', recursive=True, base_package='foo', only_names=True)
        self.assertEqual(expected, result)

    def test_import_modules_only_paths(self):
        expected = sorted(['./foo/bar/module_1/module_1', './foo/bar/module_2/module_2', './foo/bar/module_3/module_3',
                           './foo/module_a/module_a', './foo/module_b/module_b', './foo/foo'])
        result = utilities.import_dir.get_module_paths('./foo', recursive=True, base_package='foo')
        self.assertEqual(expected, result)

    def test_import_modules(self):
        expected = sorted(['./foo/bar/module_1/module_1', './foo/bar/module_2/module_2', './foo/bar/module_3/module_3',
                           './foo/module_a/module_a', './foo/module_b/module_b', './foo/foo'])
        result = utilities.import_dir.import_modules('./foo', recursive=True, base_package='foo')
        self.assertEqual(len(expected), len(result))

    def test_import_modules_only_paths_matching_names(self):
        expected = sorted(['./foo/bar/module_1/module_1', './foo/module_a/module_a'])
        result = utilities.import_dir.get_module_paths('./foo', recursive=True, base_package='foo',
                                                       matching_names=['module_1', 'module_a'])
        self.assertEqual(expected, result)

    def test_import_modules_only_names_matching_names(self):
        expected = sorted(['foo'])
        result = utilities.import_dir.get_module_names('./foo', recursive=True, base_package='foo', only_names=True,
                                                       matching_names=['foo'])
        self.assertEqual(expected, result)
