from unittest import TestCase, main

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

        # Case modules + paths
        expected = sorted(['./foo/bar/module_1/module_1', './foo/bar/module_2/module_2', './foo/bar/module_3/module_3',
                    './foo/module_a/module_a', './foo/module_b/module_b', './foo/foo'])
        result = utilities.import_dir.import_modules('./foo', recursive=True, base_package='foo', include_paths=True)
        self.assertEqual(expected, result['paths'])
        modules = result['modules']

        # Case modules
        result = utilities.import_dir.import_modules('./foo', recursive=True, base_package='foo')
        self.assertListEqual(modules, result)

        rmtree('./foo')


if __name__ == '__main__':
    main()