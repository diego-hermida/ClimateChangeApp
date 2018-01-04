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

# Regular expression of a module:
__module_file_regexp = "(.+)\.py(c?)$"
__dirs = []
__mock_packages_keyword = 'mock'

def import_modules(path, recursive=False, base_package=None, include_paths=False):
    """ Imports all modules residing in directory "path" into a alphabetically sorted list of callable <module> objects.
        :param path: Base directory to be scanned.
        :param recursive: When set to 'True', modules in all subpackages (and so on) are also imported.
        :param base_package: Python base package (use only when absolute path is provided)
        :param include_paths: Also include a list of paths, where each path indicates the absolute path of a module.
                              Paths' format is as described below:
                              <absolute path to module> <OS separator ('/' or '\'> <module_name without file extension>
        :return: A dict with two fields, if 'include_paths' has been set to True:
                    - modules: A list of <module> objects, sorted alphabetically
                    - paths: A list of <str>, sorted alphabetically
                 A list of <module> objects, if 'include_paths' is False (default)
        :rtype: dict or list
    """
    return {'modules': __import_modules(path, recursive, base_package, include_paths),
            'paths': sorted(__dirs)} if include_paths else __import_modules(path, recursive, base_package)


def __get_module_names(path, recursive=False, base_package=None, include_paths=False):
    result = []
    for entry in os.listdir(path):
        if entry == '__pycache__': continue
        full_entry = os.path.join(path, entry)
        if os.path.isdir(full_entry) and recursive:  # searches in subpackages
            result += __get_module_names(full_entry, recursive=recursive, base_package=base_package,
                                         include_paths=include_paths)
        elif os.path.isfile(full_entry):
            regexp_result = re.search(__module_file_regexp, full_entry)  # Verifies file is module
            if regexp_result:
                if '__init__' in full_entry:
                    continue
                # Replaces path separator ('/' or '\') by Python's package separator
                if include_paths:
                    __dirs.append(full_entry.replace('.py', ''))
                name = regexp_result.groups()[0].replace(os.sep, '.')
                name = name.lstrip('.') if base_package is None else name[name.find(base_package):]  # substring
                result.append(name)
    return sorted([x for x in result if not __mock_packages_keyword in x])


def __import_modules(path, recursive=False, base_package=None, include_paths=False):
    names =  __get_module_names(path, recursive=recursive, base_package=base_package,
                                                         include_paths=include_paths)
    return [import_module(x) for x in names]
