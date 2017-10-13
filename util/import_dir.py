# ---------------------------------------------------------------------------------------------------
# Based on: http://gitlab.com/aurelien-lourot/importdir
# Customized by: diego.hermida@udc.es
#   - Recursive directory search.
#   - Return modules as a list after having imported them.
# ---------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------------------------------

def import_modules(path, recursive=False, base_package=None):
    """ Imports all modules residing in directory "path" into a alphabetically sorted list of callable <module> objects.
        :param path: Base directory to be scanned.
        :param recursive: When set to 'True', modules in all subpackages (and so on) are also imported.
        :param base_package: Python base package (use only when absolute path is provided)
        :rtype: list
    """
    return __import_modules(path, recursive, base_package)


# ---------------------------------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------------------------------

import os
import re
import sys
from importlib import import_module

# File name of a module:
__module_file_regexp = "(.+)\.py(c?)$"


def __get_module_names(path, recursive=False, base_package=None):
    result = []
    for entry in os.listdir(path):
        if entry == '__pycache__': continue
        full_entry = os.path.join(path, entry)
        if os.path.isdir(full_entry) and recursive:  # searches in subpackages
            result += __get_module_names(full_entry, recursive=recursive, base_package=base_package)
        elif os.path.isfile(full_entry):
            regexp_result = re.search(__module_file_regexp, full_entry)  # Verifies file is module
            if regexp_result:
                # Replaces path separator ('/' or '\') by Python's package separator
                name = regexp_result.groups()[0].replace(os.sep, '.')
                name = name.lstrip('.') if base_package is None else name[name.find(base_package):]  # substring
                result.append(name)
    return result


def __import_modules(path, recursive=False, base_package=None):
    modules = []
    sys.path.append(path)  # adds provided directory to list we can import from
    for module_name in sorted(__get_module_names(path, recursive=recursive, base_package=base_package)):
        modules.append(import_module(module_name))  # Performs import
    return modules
