import datetime

from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import HistoricalWeatherObservation, Location
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from utilities.util import parse_float, parse_int, parse_bool
from django.db import transaction

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _HistoricalWeatherDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                                     log_to_telegram=log_to_telegram)
    return _singleton


class _HistoricalWeatherDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _check_dependencies_satisfied(self):
        self.dependencies_satisfied = Location.objects.count() > 0

    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from HistoricalWeatherDataCollector) and the Location
            Django model.
        """
        self.data = []
        for value in self.elements_to_convert:
            try:
                location = parse_int(value['location_id'], nullable=False)
                date = datetime.datetime.fromtimestamp(parse_int(value['date_utc'], nullable=False) / 1000).date()
                fog = parse_bool(value['history']['dailysummary'][0].get('fog'))
                rain = parse_bool(value['history']['dailysummary'][0].get('rain'))
                snow = parse_bool(value['history']['dailysummary'][0].get('snow'))
                hail = parse_bool(value['history']['dailysummary'][0].get('hail'))
                thunder = parse_bool(value['history']['dailysummary'][0].get('thunder'))
                tornado = parse_bool(value['history']['dailysummary'][0].get('tornado'))
                snow_fall = parse_float(value['history']['dailysummary'][0].get('snowfallm'))
                snow_depth = parse_float(value['history']['dailysummary'][0].get('snowdepthm'))
                mean_temp = parse_int(value['history']['dailysummary'][0].get('meantempm'))
                mean_pressure = parse_float(value['history']['dailysummary'][0].get('meanpressurem'))
                mean_wind_speed = parse_int(value['history']['dailysummary'][0].get('meanwindspdm'))
                mean_wind_direction = self._normalize_wind_direction(value['history']['dailysummary'][0].get('meanwdire'))
                mean_wind_direction_degrees = parse_int(value['history']['dailysummary'][0].get('meanwdird'))
                humidity = parse_int(value['history']['dailysummary'][0].get('humidity'))
                max_temp = parse_int(value['history']['dailysummary'][0].get('maxtempm'))
                max_pressure = parse_float(value['history']['dailysummary'][0].get('maxpressurem'))
                max_wind_speed = parse_int(value['history']['dailysummary'][0].get('maxwspdm'))
                min_temp = parse_int(value['history']['dailysummary'][0].get('mintempm'))
                min_pressure = parse_float(value['history']['dailysummary'][0].get('minpressurem'))
                min_wind_speed = parse_int(value['history']['dailysummary'][0].get('minwspdm'))
                precipitation = parse_float(value['history']['dailysummary'][0].get('precipm'))
                self.data.append(HistoricalWeatherObservation(location_id=location, date=date, fog=fog, rain=rain,
                        snow=snow, hail=hail, thunder=thunder, tornado=tornado, snow_fall=snow_fall, snow_depth=snow_depth,
                        mean_temp=mean_temp, mean_pressure=mean_pressure, mean_wind_speed=mean_wind_speed,
                        mean_wind_direction=mean_wind_direction, mean_wind_direction_degrees=mean_wind_direction_degrees,
                        humidity=humidity, max_temp=max_temp, max_pressure=max_pressure, max_wind_speed=max_wind_speed,
                        min_temp=min_temp, min_pressure=min_pressure, min_wind_speed=min_wind_speed,
                        precipitation=precipitation))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. HistoricalWeatherObservation with ID "%s" '
                        'will not be converted.' % _id)

    @staticmethod
    def _normalize_wind_direction(wind_direction: str):
        if wind_direction is None:
            return None
        elif len(wind_direction) > 3:
            return wind_direction[0].upper()
        else:
            return wind_direction

    @transaction.atomic
    def _save_data(self):
        """
            Saves collected data into a relational database, using the Django ORM.
            Operation is efficient, since the "bulk_create" is used instead of N calls to "create".
            Postcondition: If operation succeeds, "self.data" variable is dereferenced, allowing GC to free up memory.
        """
        super()._save_data()
        if self.data:
            self.state['inserted_elements'] = len(HistoricalWeatherObservation.objects.bulk_create(self.data))
            self.logger.info('Successfully saved %d elements.' % self.state['inserted_elements'])
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
