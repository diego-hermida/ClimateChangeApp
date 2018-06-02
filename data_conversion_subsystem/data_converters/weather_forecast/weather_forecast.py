from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import WeatherForecastObservation, Location, WeatherType
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from utilities.util import parse_float, parse_int, compute_wind_direction, parse_date_utc
from django.db import transaction

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _WeatherForecastDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                                   log_to_telegram=log_to_telegram)
    return _singleton


class _WeatherForecastDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _check_dependencies_satisfied(self):
        self.dependencies_satisfied = Location.objects.exists() and WeatherType.objects.exists()

    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from WeatherForecastDataCollector) and the Location
            Django model.
        """
        self.data = []
        items = 0
        for value in self.elements_to_convert:
            try:
                location = parse_int(value.get('location_id'), nullable=False)
                if not value.get('list', []):
                    continue
                for obs in value['list']:
                    items += 1
                    # Setting timezone to pytz.UTC FIXES [BUG-039].
                    timestamp = parse_date_utc(obs.get('dt') * 1000)
                    date = timestamp.date()
                    time = timestamp.time()
                    temperature = parse_int(obs['main'].get('temp'))
                    pressure = parse_float(obs['main'].get('pressure'))
                    humidity = parse_int(obs['main'].get('humidity'))
                    wind_speed = parse_int(obs.get('wind', {}).get('speed'))
                    wind_degrees = parse_int(obs.get('wind', {}).get('deg'))
                    wind_direction = compute_wind_direction(wind_degrees)
                    weather = obs.get('weather', [{}])[0]
                    if weather.get('icon') and weather.get('id'):
                        weather = - parse_int(weather.get('id'), nullable=False) if 'n' in weather['icon'] else \
                                parse_int(weather.get('id'), nullable=False)
                    self.data.append(WeatherForecastObservation(location_id=location, date=date, time=time,
                            temperature=temperature, pressure=pressure, humidity=humidity, wind_speed=wind_speed,
                            wind_degrees=wind_degrees, wind_direction=wind_direction, weather_id=weather))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. WeatherForecastObservation with ID "%s" '
                        'will not be converted.' % _id)
        self.state['elements_to_convert'] = items

    @transaction.atomic
    def _save_data(self):
        """
            Saves collected data into a relational database, using the Django ORM.
            Operation is efficient, since the "bulk_create" is used instead of N calls to "create".
            Postcondition: If operation succeeds, "self.data" variable is dereferenced, allowing GC to free up memory.
        """
        super()._save_data()
        if self.data:
            # FIXES [BUG-034].
            WeatherForecastObservation.objects.all().delete()
            self.state['inserted_elements'] = len(WeatherForecastObservation.objects.bulk_create(self.data))
            self.logger.info('Successfully saved %d elements.' % self.state['inserted_elements'])
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
