from data_conversion_subsystem.settings import register_settings

# Necessary to work with Django and PyPy3.
register_settings()

from data_conversion_subsystem.data.models import Location, Country
from data_conversion_subsystem.data_converter.data_converter import DataConverter
from django.db import transaction
from utilities.util import parse_float, parse_int, parse_date_utc

_singleton = None


def instance(log_to_file=True, log_to_stdout=True, log_to_telegram=None) -> DataConverter:
    global _singleton
    if not _singleton or _singleton and _singleton.finished_execution():
        _singleton = _LocationsDataConverter(log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                                             log_to_telegram=log_to_telegram)
    return _singleton


class _LocationsDataConverter(DataConverter):

    def __init__(self, log_to_file=True, log_to_stdout=True, log_to_telegram=None):
        super().__init__(file_path=__file__, log_to_file=log_to_file, log_to_stdout=log_to_stdout,
                         log_to_telegram=log_to_telegram)

    def _check_dependencies_satisfied(self):
        self.dependencies_satisfied = Country.objects.exists()

    @transaction.atomic
    def _perform_data_conversion(self):
        """
            Performs data conversion between JSON data (from LocationsDataCollector) and the Location
            Django model.
        """
        self.data = []
        for value in self.elements_to_convert:
            try:
                id = value['_id']
                name = value['name'].strip()
                country_id = value['country_code']
                climate_zone = value['climate_zone']
                elevation = parse_int(value['elevation'].get('value'))
                elevation_units = 'M' if elevation is not None else None
                # Setting timezone to pytz.UTC FIXES [BUG-039].
                last_modified = parse_date_utc(value['last_modified'])
                latitude = parse_float(value.get('latitude'))
                longitude = parse_float(value.get('longitude'))
                population = parse_int(value.get('population'))
                timezone = value.get('timezone')
                owm_data = value.get('owm_station_id') is not None
                # Changing permuted values FIXES [BUG-038].
                wunderground_data = value.get('wunderground_loc_id') is not None
                air_pollution_data = value.get('waqi_station_id') is not None
                self.data.append(Location(id=id, name=name, country_id=country_id, climate_zone=climate_zone,
                        elevation=elevation, elevation_units=elevation_units, last_modified=last_modified,
                        longitude=longitude, latitude=latitude, population=population, timezone=timezone,
                        owm_data=owm_data, wunderground_data=wunderground_data, air_pollution_data=air_pollution_data))
            except (ValueError, AttributeError, KeyError, IndexError, TypeError):
                _id = value.get('_id', 'Unknown ID')
                self.logger.exception('An error occurred while parsing data. Location with ID "%s" will not be '
                        'converted.' % _id)

    @transaction.atomic
    def _save_data(self):
        """
            Saves collected data into a relational database, using the Django ORM.
            This operation cannot be as efficient as a "bulk insert", since inserted data isn't always new, and a
            "IntegrityError" would be raised. Thus, data is updated if exists, and created (using one "bulk insert") if
            not.
            Postcondition: If operation succeeds, "self.data" variable is dereferenced, allowing GC to free up memory.
        """
        super()._save_data()
        if self.data:
            updated = 0
            inserted = 0
            bulk_insert = []
            for l in self.data:
                if Location.objects.filter(pk=l.id).exists():
                    Location.objects.filter(pk=l.id).update(elevation=l.elevation, elevation_units=l.elevation_units,
                            last_modified=l.last_modified, population=l.population, owm_data=l.owm_data,
                            wunderground_data=l.wunderground_data, air_pollution_data=l.air_pollution_data,
                            timezone=l.timezone)
                    updated += 1
                else:
                    bulk_insert.append(l)
            if bulk_insert:
                inserted = len(Location.objects.bulk_create(self.data))
            self.state['inserted_elements'] = inserted + updated
            self.logger.debug('Successfully saved %d elements.\n\t- Inserted (bulk insert): %d.\n\t- Updated: %d.' %
                    (self.state['inserted_elements'], inserted, updated))
        else:
            self.logger.info('No elements were saved because no elements were available.')
        self.data = None
