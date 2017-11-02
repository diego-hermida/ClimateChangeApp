import datetime
from random import uniform, choice
from threading import Lock
from time import sleep

from utilities.util import DataCollector, get_config, get_module_name, read_state, serialize_date, deserialize_date, \
    write_state

lock = Lock()


def instance() -> DataCollector:
    return __MockDataCollector()


class __MockDataCollector(DataCollector):
    def __init__(self):
        super().__init__()
        self.__data = None
        self.__state = None
        self.__worktime = choice([True, False])
        self.__config = get_config(__file__)
        self.__module_name = get_module_name(__file__)

    def restore_state(self):
        """
           Restores previous saved state (.state) if valid. Otherwise, creates a valid structure
           for .state file from the STATE_STRUCT key in .config file.
           State manipulation is thread-safe, since a Lock is used to access shared .state file.
        """
        global lock
        lock.acquire()
        self.__state = read_state(__file__, repair_struct=self.__config['STATE_STRUCT'])
        lock.release()
        self.__state['last_request'] = deserialize_date(self.__state['last_request'])

    def worktime(self) -> bool:
        """
            Determines whether this module is ready or not to perform new work, according to "worktime" parameter passed
            to constructor.
            :return: True if it's work time, False otherwise.
            :rtype: bool
        """
        return self.__worktime

    def collect_data(self):
        """
            Performs a mock "collect data" operation which takes a random time between MIN_TIME and MAX_TIME.
            Parameters are read from configuration file (ocean_mass.config)
        """
        sleep(uniform(self.__config['MIN_TIME'], self.__config['MAX_TIME']))
        self.__state['last_request'] = datetime.datetime.now()

    def save_data(self):
        """
           Performs a mock "save data" operation.
        """
        sleep(self.__config['MIN_TIME'])

    def save_state(self):
        """
            Serializes state to .state file in such a way that can be deserialized later.
            State manipulation is thread-safe, since a Lock is used to access shared .state file.
        """
        self.__state['last_request'] = serialize_date(self.__state['last_request'])
        global lock
        lock.acquire()
        write_state(self.__state, __file__)
        lock.release()

    def auto_validate_state(self):
        sleep(self.__config['VALIDATE_TIME'])

    def __repr__(self):
        return str(__class__.__name__) + ' [' \
            '\n\t(*) config: ' + self.__config.__repr__() + \
            '\n\t(*) data: ' + self.__data.__repr__() + \
            '\n\t(*) module_name: ' + self.__module_name.__repr__() + \
            '\n\t(*) state: ' + self.__state.__repr__() + ']'
