import yaml

from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.config.config import DCS_CONFIG
from data_conversion_subsystem.data.models import CurrentConditionsObservation, Location, WeatherType
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from utilities.util import parse_float, parse_int, parse_date_utc, compute_wind_direction
from django.db import transaction

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _CurrentConditionsDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                                     log_to_telegram=log_to_telegram)
    return _singleton


class _CurrentConditionsDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _check_dependencies_satisfied(self):
        self.dependencies_satisfied = Location.objects.count() > 0

    @transaction.atomic
    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from CurrentConditionsDataCollector) and the Location
            Django model.
        """
        self.data = []
        if not self.state['weather_types_created']:
            with open(DCS_CONFIG['ROOT_DATA_CONVERSION_SUBSYSTEM_FOLDER'] + self.config['RESOURCE_FILEPATH'], 'r') as f:
                weather_types = yaml.load(f)['WEATHER_TYPES']
            types = []
            for type in weather_types:
                try:
                    id = type['id']
                    description = type['description']
                    icon = type['icon']
                    types.append(WeatherType(id=id, description=description, icon_code=icon))
                except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                    _id = type.get('id', 'Unknown name')
                    self.logger.exception('An error occurred while parsing data. IndicatorDetails "%s" will not be '
                            'created. Therefore, Indicators with such IndicatorDetails would not be created, either. '
                            'Data conversion will stop now.' % _id)
                    self.advisedly_no_data_converted = True
                    return
            created = len(WeatherType.objects.bulk_create(types))
            self.logger.info('Created %d WeatherType(s) (out of %d).' % (created, len(weather_types)))
            self.state['weather_types_created'] = True
        for value in self.elements_to_convert:
            try:
                location = parse_int(value['location_id'], nullable=False)
                # Setting timezone to pytz.UTC FIXES [BUG-039].
                timestamp = parse_date_utc(value['time_utc'])
                temperature = parse_int(value['main'].get('temp'))
                pressure = parse_float(value['main'].get('pressure'))
                humidity = parse_int(value['main'].get('humidity'))
                wind_speed = parse_int(value.get('wind', {}).get('speed'))
                wind_degrees = parse_int(value.get('wind', {}).get('deg'))
                wind_direction = compute_wind_direction(wind_degrees)
                int_sunrise = parse_int(value.get('sys', {}).get('sunrise'))
                int_sunset = parse_int(value.get('sys', {}).get('sunset'))
                sunrise = None if int_sunrise is None else parse_date_utc(int_sunrise)
                sunset = None if int_sunset is None else parse_date_utc(int_sunset)
                weather = value.get('weather', [{}])[0]
                if weather.get('icon') and weather.get('id'):
                    weather = - parse_int(weather.get('id'), nullable=False) if 'n' in weather['icon'] else parse_int(
                            weather.get('id'), nullable=False)
                self.data.append(CurrentConditionsObservation(location_id=location, timestamp=timestamp,
                        temperature=temperature, pressure=pressure, humidity=humidity, wind_speed=wind_speed,
                        wind_degrees=wind_degrees, wind_direction=wind_direction, sunrise=sunrise, sunset=sunset,
                        weather_id=weather))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. CurrentConditionsObservation with ID "%s" '
                        'will not be converted.' % _id)

    @transaction.atomic
    def _save_data(self):
        """
            Saves collected data into a relational database, using the Django ORM.
            Operation is efficient, since the "bulk_create" is used instead of N calls to "create".
            All data is updated each time
            Postcondition: If operation succeeds, "self.data" variable is dereferenced, allowing GC to free up memory.
        """
        super()._save_data()
        if self.data:
            # FIXES [BUG-034]
            CurrentConditionsObservation.objects.all().delete()
            self.state['inserted_elements'] = len(CurrentConditionsObservation.objects.bulk_create(self.data))
            self.logger.info('Successfully saved %d elements.' % self.state['inserted_elements'])
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
