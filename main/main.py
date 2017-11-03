import data_modules.mock_data_collector.mock_data_collector as mock_module
import supervisor.supervisor as supervisor
import threading

from queue import Queue
from utilities.import_dir import import_modules
from utilities.util import get_config

__config = get_config(__file__)
__channel = None
__condition = threading.Condition()


class __DataCollectorThread(threading.Thread):
    def __init__(self, data_module):
        self.__module = data_module
        self.__data_collector = data_module.instance()
        threading.Thread.__init__(self)
        self.setName(self.__data_collector.__class__.__name__.replace('__', '') + 'Thread')

    def run(self):
        self.__data_collector.restore_state()
        if self.__data_collector.worktime():
            self.__data_collector.collect_data()
            self.__data_collector.save_data()
            self.__data_collector.save_state()
        else:
            pass

    def join(self, timeout=None):
        threading.Thread.join(self, timeout=timeout)
        return self.__module


class __SupervisorThread(threading.Thread):
    def __init__(self, queue: Queue, condition: threading.Condition):
        self.__supervisor = supervisor.instance(queue, condition)
        threading.Thread.__init__(self)
        self.setName('SupervisorThread')

    def run(self):
        self.__supervisor.supervise()


if __name__ == '__main__':
    if __config['MOCK_EXECUTION']:
        modules = list()
        for i in range(__config['MOCK_MODULES']):
            modules.append(mock_module)
    else:
        # Dynamically, recursively imports all Python modules under base directory (and returns them in a list)
        modules = import_modules(__config['MODULE_PATH'], recursive=True, base_package=__config['BASE_PACKAGE'])

    threads = []
    __channel = Queue(maxsize=len(modules) + 1)   # Enabling a channel to pass data between Main and Supervisor
    supervisor = __SupervisorThread(__channel, __condition)
    supervisor.start()
    for m in modules:
        thread = __DataCollectorThread(m)
        threads.append(thread)
        thread.start()
    for thread in threads:
        m = thread.join()  # Overriden join method returns <module> object
        __condition.acquire()
        __channel.put_nowait(m)
        __condition.notify()
        __condition.release()
    __channel.put_nowait("exit")  # Exit message.
