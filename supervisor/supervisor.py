from queue import Queue
from threading import Condition
from utilities.util import get_config, get_module_name

__singleton = None


def instance(queue: Queue, condition: Condition):
    global __singleton
    if __singleton is None:
        __singleton = __Supervisor(queue, condition)
    return __singleton


class __Supervisor:
    def __init__(self, queue: Queue, condition: Condition):
        super().__init__()
        self.__queue = queue
        self.__condition = condition
        self.__exit = False
        self.__state = None
        self.__config = get_config(__file__)
        self.__module_name = get_module_name(__file__)

    def supervise(self):
        while not self.__exit:
            item = None
            self.__condition.acquire()
            while True:
                if not self.__queue.empty():
                    item = self.__queue.get_nowait()
                    break
                self.__condition.wait()
            self.__condition.release()
            if isinstance(item, str) and item == self.__config['EXIT_MSG']:
                self.__exit = True
            else:
                data_collector = item.instance()
                data_collector.auto_validate_state()  # Each module validates its state
