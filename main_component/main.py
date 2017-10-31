import threading

from utilities.import_dir import import_modules
from utilities.util import get_config

__config = get_config(__file__)


class __DataCollectorThread(threading.Thread):
    def __init__(self, data_module):
        self.__data_collector = data_module.instance()
        threading.Thread.__init__(self)

    def run(self):
        self.__data_collector.restore_state()
        if self.__data_collector.worktime():
            self.__data_collector.collect_data()
            self.__data_collector.save_data()
            self.__data_collector.save_state()
        else:
            pass


if __name__ == '__main__':
    # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
    modules = import_modules(__config['MODULE_PATH'], recursive=True, base_package=__config['BASE_PACKAGE'])
    threads = []
    for m in modules:
        t = __DataCollectorThread(m)
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
