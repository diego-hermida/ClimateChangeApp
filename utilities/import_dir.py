# ---------------------------------------------------------------------------------------------------
# Based on: http://gitlab.com/aurelien-lourot/importdir
# Customized by: diego.hermida@udc.es
#   - Recursive directory search.
#   - Return modules as a list after having imported them.
#   - Return paths as list (optional)
# ---------------------------------------------------------------------------------------------------

import os
import re

from importlib import import_module
from utilities.util import get_module_name

# Regular expression of a module:
_module_file_regexp = "(.+)\.py(c?)$"
_dirs = []
_mock_packages_keyword = 'mock'


def import_modules(path, recursive=False, base_package=None) -> list:
    """
        Imports all modules residing in directory "path" into a alphabetically sorted list of callable <module> objects.
        :param path: Base directory to be scanned.
        :param recursive: When set to 'True', modules in all subpackages (and so on) are also imported.
        :param base_package: Python base package (use only when absolute path is provided)
        :return: A list of <module> objects, if 'include_paths' is False (default)
        :rtype: list
    """
    names = _get_module_names(path, recursive=recursive, base_package=base_package)
    return [import_module(x) for x in names]


def get_module_names(path, recursive=False, base_package=None, only_names=False) -> list:
    """
        Retrieves all module names residing in directory "path", sorted alphabetically.
        :param path: Base directory to be scanned.
        :param recursive: When set to 'True', module names in all subpackages (and so on) are also retrieved.
        :param base_package: Python base package (use only when absolute path is provided)
        :param only_names: If 'True', retrieves only the module names (e.g. my_module). Otherwise, module names also
                           contain their packages (e.g. foo.bar.my_module).
        :return: A list of module names.
        :rtype: list
    """
    global _dirs
    _dirs = []
    result = _get_module_names(path, recursive=recursive, base_package=base_package, include_paths=only_names)
    return result if not only_names else sorted([get_module_name(x) for x in _dirs])


def get_module_paths(path, recursive=False, base_package=None):
    """
        Retrieves all module paths residing in directory "path", sorted alphabetically.
        :param path: Base directory to be scanned.
        :param recursive: When set to 'True', module paths in all subpackages (and so on) are also retrieved.
        :param base_package: Python base package (use only when absolute path is provided)
        :return: A list of module names.
        :rtype: list
    """
    global _dirs
    _dirs = []
    _get_module_names(path, recursive=recursive, base_package=base_package, include_paths=True)
    return sorted(_dirs)


def _get_module_names(path, recursive=False, base_package=None, include_paths=False) -> list:
    result = []
    for entry in os.listdir(path):
        if entry == '__pycache__': continue
        full_entry = os.path.join(path, entry)
        if os.path.isdir(full_entry) and recursive:  # searches in subpackages
            result += _get_module_names(full_entry, recursive=recursive, base_package=base_package,
                                         include_paths=include_paths)
        elif os.path.isfile(full_entry):
            regexp_result = re.search(_module_file_regexp, full_entry)  # Verifies file is module
            if regexp_result:
                if '__init__' in full_entry:
                    continue
                # Replaces path separator ('/' or '\') by Python's package separator
                if include_paths:
                    _dirs.append(full_entry.replace('.py', ''))
                name = regexp_result.groups()[0].replace(os.sep, '.')
                name = name.lstrip('.') if base_package is None else name[name.find(base_package):]  # substring
                result.append(name)
    return sorted([x for x in result if not _mock_packages_keyword in x])
