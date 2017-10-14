import itertools

from ftplib import FTP
from utilities.db_util import connect
from utilities.util import DataCollector, decimal_date_to_string, get_config, get_module_name, Reader, MeasureUnits, \
    MassType

__singleton = None


def instance() -> DataCollector:
    global __singleton
    if __singleton is None:
        __singleton = __OceanMassDataCollector()
    return __singleton


class __OceanMassDataCollector(DataCollector):
    def __init__(self):
        super().__init__()
        self.__data = []
        self.__state = None
        self.__config = get_config(__file__)
        self.__module_name = get_module_name(__file__)

    def restore_state(self):
        pass

    def worktime(self) -> bool:
        pass

    def get_data(self):
        """
            Obtains data from the NASA servers via FTP:
                - Antarctica ice mass.
                - Greenland ice mass.
                - Ocean mass height.
            Parameters are read from configuration file (ocean_mass.config)
        """
        ftp = FTP(self.__config['URL'])
        ftp.login()
        ftp.cwd(self.__config['DATA_DIR'])  # Accessing directory
        file_names = sorted([x for x in ftp.nlst() if x.endswith(self.__config['FILE_EXT'])])
        for name in file_names:
            r = Reader()
            ftp.retrlines('RETR ' + name, r)
            self.__data.append(self.__to_json(r.data, self.__get_type(name)))
        ftp.quit()
        self.__data = list(itertools.chain.from_iterable(self.__data))

    def save_data(self):
        """
           Saves data into a persistent storage system (Currently, a MongoDB instance).
           Data is saved in a collection with the same name as the module.
        """
        connection = connect(self.__module_name)
        connection.insert_many(self.__data)

    def save_state(self):
        pass

    @staticmethod
    def __get_type(file_name):
        if MassType.antarctica in file_name:
            return MassType.antarctica
        elif MassType.greenland in file_name:
            return MassType.greenland
        elif MassType.ocean in file_name:
            return MassType.ocean

    def __to_json(self, data, data_type):
        json_data = []
        if data_type is MassType.ocean:
            for line in data:
                fields = line.split()
                date = decimal_date_to_string(float(fields[0]), self.__config['DATE_FORMAT'])
                measure = {'_id': data_type + '_' + date, 'date': date, 'type': data_type, 'measures': []}
                measure['measures'].append({'height': fields[1], 'units': MeasureUnits.mm})
                measure['measures'].append({'uncertainty': fields[2], 'units': MeasureUnits.mm})
                measure['measures'].append({'height_deseasoned': fields[3], 'units': MeasureUnits.mm})
                json_data.append(measure)
        else:
            for line in data:
                fields = line.split()
                date = decimal_date_to_string(float(fields[0]), self.__config['DATE_FORMAT'])
                measure = {'_id': data_type + '_' + date, 'date': date, 'type': data_type, 'measures': []}
                measure['measures'].append({'mass': fields[1], 'units': MeasureUnits.Gt})
                measure['measures'].append({'uncertainty': fields[2], 'units': MeasureUnits.Gt})
                json_data.append(measure)
        return json_data
