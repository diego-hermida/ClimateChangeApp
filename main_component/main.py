from utilities.import_dir import import_modules
from utilities.util import get_config, DataCollector

__config = get_config(__file__)

if __name__ == '__main__':
    # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
    modules = import_modules(__config['MODULE_PATH'], recursive=True, base_package=__config['BASE_PACKAGE'])
    for m in modules:
        t = DataCollector(m)
        t.start()
        t.join()
