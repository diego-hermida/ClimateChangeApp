import copy
import operator

from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import AirPollutionMeasure, Location
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from utilities.util import parse_float, parse_int, parse_date_utc
from django.db import transaction

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _AirPollutionDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout, log_to_telegram=log_to_telegram)
    return _singleton


class _AirPollutionDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _check_dependencies_satisfied(self):
        self.dependencies_satisfied = Location.objects.exists()

    @transaction.atomic
    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from AirPollutionDataCollector) and the Location
            Django model.
        """
        self.data = []
        previous_cache = copy.deepcopy(self.state['cache'])
        for value in self.elements_to_convert:
            try:
                location = parse_int(value['location_id'], nullable=False)
                dominant_pollutant = None if value['data'].get('dominentpol') is None else value['data'][
                        'dominentpol'].upper()
                # Setting timezone to pytz.UTC FIXES [BUG-039].
                timestamp = parse_date_utc(value['time_utc'])
                timestamp_epoch = parse_int(value['time_utc'], nullable=False)
                co_aqi = parse_float(value['data']['iaqi'].get('co', {}).get('v'))
                no2_aqi = parse_float(value['data']['iaqi'].get('no2', {}).get('v'))
                o3_aqi = parse_float(value['data']['iaqi'].get('o3', {}).get('v'))
                pm25_aqi = parse_float(value['data']['iaqi'].get('pm25', {}).get('v'))
                pm10_aqi = parse_float(value['data']['iaqi'].get('pm10', {}).get('v'))
                so2_aqi = parse_float(value['data']['iaqi'].get('so2', {}).get('v'))
                attributions = value['data'].get('attributions')
                cache = self.state['cache'].get(location, [])
                dominant_pollutant_value, dominant_pollutant_color, dominant_pollutant_text_color = \
                    AirPollutionMeasure.get_dominant_pollutant_values(dominant_pollutant,
                            {AirPollutionMeasure.CO: co_aqi, AirPollutionMeasure.NO2: no2_aqi,
                             AirPollutionMeasure.O3: o3_aqi, AirPollutionMeasure.PM25: pm25_aqi,
                             AirPollutionMeasure.PM10: pm10_aqi, AirPollutionMeasure.SO2: so2_aqi})
                if attributions and next((a for a in cache if a['url'] in [x['url'] for x in attributions] and
                        a['name'] in [x['name'] for x in attributions]), default=None) is None:
                    cache.extend(attributions)
                    self.state['cache'][location] = cache
                self.data.append(AirPollutionMeasure(location_id=location, dominant_pollutant=dominant_pollutant,
                        timestamp=timestamp, co_aqi=co_aqi, no2_aqi=no2_aqi, o3_aqi=o3_aqi, pm25_aqi=pm25_aqi,
                        pm10_aqi=pm10_aqi, so2_aqi=so2_aqi, dominant_pollutant_value=dominant_pollutant_value,
                        dominant_pollutant_color=dominant_pollutant_color, timestamp_epoch=timestamp_epoch,
                        dominant_pollutant_text_color=dominant_pollutant_text_color))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. AirPollutionMeasure with ID "%s" will not '
                        'be converted.' % _id)
        for entry in self.state['cache']:
            if previous_cache.get(entry) is None or str(previous_cache[entry]) != str(self.state['cache'][entry]):
                self.state['cache'][entry] = sorted(self.state['cache'][entry], key=lambda k: k['url'])
                loc = Location.objects.get(pk=entry)
                loc.air_pollution_attributions = self.state['cache'][entry]
                self.logger.debug('Updating air pollution attributions for the location: %s.' % loc.name)
                loc.save()

    @transaction.atomic
    def _save_data(self):
        """
            Saves collected data into a relational database, using the Django ORM.
            Operation is efficient, since the "bulk_create" is used instead of N calls to "create".
            Postcondition: If operation succeeds, "self.data" variable is dereferenced, allowing GC to free up memory.
        """
        super()._save_data()
        if self.data:
            self.data = AirPollutionMeasure.objects.bulk_create(self.data)
            self.state['inserted_elements'] = len(self.data)
            self.logger.info('Successfully saved %d elements.' % self.state['inserted_elements'])
            self.logger.info('Updating references to AirPollutionMeasure from Location objects.')
            # Using operator.attrgeter as sort function instead of implementing comparison operators due to:
            # https://stackoverflow.com/questions/403421/how-to-sort-a-list-of-objects-based-on-an-attribute-of-the-objects
            self.data.sort(key=operator.attrgetter('timestamp'), reverse=True)
            updated_locations = []
            for value in self.data:
                if value.location_id in updated_locations:
                    continue
                else:
                    loc = Location.objects.get(pk=value.location_id)
                    loc.air_pollution_last_measure = value
                    self.logger.debug('Updating air pollution\'s last measure for the location: %s.' % loc.name)
                    loc.save()
                    updated_locations.append(value.location_id)
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
