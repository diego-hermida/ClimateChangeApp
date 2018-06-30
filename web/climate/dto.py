from django.utils.translation import ugettext_lazy as _

from data_conversion_subsystem.data.models import AirPollutionMeasure, OceanMassMeasure, RpcDatabaseEmission
from utilities.util import parse_date_utc


class LocationDto:

    def __init__(self, location, has_air_pollution_data, has_historical_weather_data, air_pollution_last_measure,
                 current_conditions, weather_forecast):
        """
            Initializes a LocationDto object. All of these fields can be obtained by invoking the LocationService.
            :param location: A Location object.
            :param has_air_pollution_data: Whether the Location has air pollution data or not.
            :param has_historical_weather_data: Whether the Location has historical weather data or not.
            :param air_pollution_last_measure: An AirPollutionMeasure object. This must be the latest available measure.
            :param current_conditions: A CurrentConditionsObservation object.
            :param weather_forecast: A list of WeatherForecastObservation objects, with all the forecast data.
        """
        self.location = location
        self.current_conditions = current_conditions
        self.weather_forecast = LocationDto.normalize_weather_forecast_data(weather_forecast[0], weather_forecast[1])
        self.location.air_pollution_data = has_air_pollution_data
        self.air_pollution = self.normalize_last_air_pollution_measure(air_pollution_last_measure)
        self.is_capital_city = self.location.name == self.location.country.capital_city_name
        self.location.owm_data = location.owm_data and self.current_conditions and self.weather_forecast
        self.location.wunderground_data = has_historical_weather_data
        self.has_all_data = self.location.owm_data and self.location.wunderground_data and self.location.air_pollution_data
        self.i18n()

    def i18n(self):
        """
            This method encapsulates the internationalization of all translatable fields. These are:
                - Descriptions of metheorological phenomena.
                - Name of the Location.
                - Name of the Country.
                - Name of the Income level.
                - Name of the Country region.
        """
        if self.current_conditions:
            self.current_conditions.weather.description = _(self.current_conditions.weather.description)
        if self.location:
            self.location.name = _(self.location.name)
            self.location.country.name = _(self.location.country.name)
            self.location.country.income_level.name = _(self.location.country.income_level.name)
            self.location.country.region.name = _(self.location.country.region.name)

    @staticmethod
    def normalize_last_air_pollution_measure(measure):
        """
            Converts an AirPollutionMeasure object to a `dict`, containing the required values for displaying its data.
            :param measure: An AirPollutionMeasure object.
            :return: A `dict` object.
        """
        return {'last_measure': {'last_modified': measure.timestamp,
                                 'dominant_pollutant': {'value': measure.get_dominant_pollutant_value_display(),
                                                        'color': measure.get_dominant_pollutant_color_display(),
                                                        'code': measure.get_dominant_pollutant_display(),
                                                        'text_color': measure.get_dominant_pollutant_text_color_display()},
                                 'health_issue': measure.display_health_warning(), 'measures': measure.get_measures()},
                'measures': []} if measure else None

    @staticmethod
    def normalize_weather_forecast_data(forecast, temperatures_per_day, min_forecasts=2, max_days=3) -> list:
        """
            Given the following data:
                - Min and Max temperatures, per day.
                - Hour and icon to display for each forecast observation.
            Returned values will have the following structure:
                [{'date': datetime.date, 'max_temp': int, 'min_temp', int,
                  'forecast': [{'hour': int, 'icon': str}, ...],  ...]

        :param forecast: A list of WeatherForecastObservation objects.
        :param temperatures_per_day: A list of weather forecast statistics (max and min temperatures, per day).
        :param min_forecasts: Removes data for those days having `min_forecasts` or less records.
        :param max_days: Limits the data to the `max_days` first days.
        :return: A list of `dict` objects, containing the data previously described.
        """
        if not forecast:
            return []
        weather_forecast = {}
        for day in temperatures_per_day:
            weather_forecast[day['date']] = {'max_temp': day['temperature__max'], 'min_temp': day['temperature__min'],
                                             'date': day['date'].strftime('%m/%d'), 'forecast': []}
        for record in forecast:
            weather_forecast[record['date']]['forecast'].append(
                    {'icon': record['weather__icon_code'], 'hour': record['time'].strftime('%H'),
                     'description': _(record['weather__description'])})
        return [x for x in weather_forecast.values() if len(x['forecast']) > min_forecasts][:max_days]

    def __str__(self):
        return 'LocationDto [location: %s, current_conditions: %s, weather_forecast: %s, air_pollution %s]' % (
            self.location, self.current_conditions, self.weather_forecast, self.air_pollution)

    def __repr__(self):
        return self.__str__()


class AirPollutionDto:

    @staticmethod
    def get_statistics(measures: list) -> list:
        """
            Given a list of AirPollution statistics, computes them to retrieve the max, min and average values for all
            pollutant.
            Each number represents an AQI level, and has a related color to describe it. These colors are also added
            here.
            :param measures: A list of air pollution statistics. This method expects a list of tuples. Each tuple
                             represents the values for all pollutants, as follows: (x.timestamp_epoch, x.co_aqi,
                             x.no2_aqi, x.o3_aqi, x.pm25_aqi, x.pm10_aqi).
            :return: A list, containing the max, min and average values for all pollutants. The concrete values are
                     `dict` objects, with 3 keys: 'v' for the value, 'bg' for the background color and 't' for the color
                     of the text.
        """
        if not measures:
            return []
        stats = [[0, None, None, 0], [0, None, None, 0], [0, None, None, 0], [0, None, None, 0], [0, None, None, 0]]
        for m in measures:
            for i in range(1, 6):
                if m[i] is not None:
                    j = i - 1
                    stats[j][0] += 1
                    stats[j][3] += m[i]
                    if m[i] > (stats[j][1] if stats[j][1] is not None else -1):
                        stats[j][1] = m[i]
                    if m[i] < (stats[j][2] if stats[j][2] is not None else 1000):
                        stats[j][2] = m[i]
        for i in range(5):
            stats[i][0] = AirPollutionDto._with_color(None if stats[i][0] == 0 else stats[i][3] / stats[i][0])
            stats[i][1] = AirPollutionDto._with_color(stats[i][1])
            stats[i][2] = AirPollutionDto._with_color(stats[i][2])
            stats[i][3] = AirPollutionDto._with_color(stats[i][3])
            stats[i] = stats[i][:-1]
        return stats

    @staticmethod
    def _with_color(value: float):
        """
            Given a numeric value, converts this value to a `dict` with 3 keys: 'v' for the value, 'bg' for the
            background color and 't' for the color of the text.
            :param value: A number, representing an pollutant value, using the AQI scale.
            :return: A `dict` object.
        """
        bg, t = AirPollutionMeasure.get_colors_display(value)
        return {'v': value, 'bg': bg, 't': t}

    @staticmethod
    def get_pollutant_statistics(dom_pollutants: list) -> (int, list):
        """
            Given a list of dominant pollutants, retrieves the number of measures and a list, containing the percentage
            for each dominant pollutant.
            :param dom_pollutants: A list of dominant pollutants. These must be values of
                                   AirPollutionMeasure.POLLUTANT_TYPE.
            :return: An integer, as the count of all pollutant measures; and a list of percentages. Each percentage is
                     represented as a `dict` object, with 2 keys: 'l' for the label of the pollutant (representative
                     name) and 'v' for the percentage.
        """
        if dom_pollutants is None:
            return []
        temp = {}
        for m in dom_pollutants:
            if m is None or m == '':
                continue
            if temp.get(m) is not None:
                temp[m] += 1
            else:
                temp[m] = 1
        display_values = dict(AirPollutionMeasure.POLLUTANT_TYPE)
        total_values = sum([temp[key] for key in temp])
        stats = [{'l': display_values[key], 'v': (temp[key] / total_values) * 100} for key in temp]
        return total_values, stats


class HistoricalWeatherDto:

    @staticmethod
    def normalize_data(measures: list) -> (int, int, int, int, int, dict):
        """
            Normalizes historical weather data. To do so, computes:
                - The number of measures.
                - The date of the first value.
                - The date of the last value.
                - The year of the first value.
                - The year of the last value.
                - A `dict` containing all measures.
            :param measures: A list of HistoricalWeatherObservation values, as `tuple` objects. Each tuple is composed
                             by a timestamp and the temperature (max, min or avg).
            :return: The computed elements, described before.
        """
        if not measures:
            return 0, None, None, None, None, {}
        return len(measures), measures[0][0], measures[-1][0], parse_date_utc(measures[0][0]).year, parse_date_utc(
                measures[-1][0]).year, {int(x[0] / 1000): x[1] for x in measures}


class SeaLevelRiseDto:

    @staticmethod
    def get_last_year_stats(data: list) -> (int, float):
        """
            Retrieves the evolution of sea level rise since the last year.
            :param data: A list of SeaLevelRiseMeasure objects.
            :return: A `tuple`, containing the last year and the sea level rise evolution since the previous year.
        """
        if not data:
            return None, None
        last_year = data[-1][2]
        sum_values = 0
        count = 0
        latest_value = 0
        for v in reversed(data):  # Optimising list access since values are sorted by date
            if v[2] == last_year:
                sum_values += v[1]
                count += 1
                continue
            latest_value = v[1]
            break
        return last_year, ((sum_values / count) - latest_value) if count > 0 else None


class OceanMassMeasureDto:

    @staticmethod
    def normalize_data(data: list) -> (list, list):
        """
            Separates Arctic and Antarctica data.
            :param data: A list of OceanMass measures.
            :return: Two lists, one with Arctic values and another one with Antarctica values.
        """
        arctic_data = []
        antarctica_data = []
        for v in data:
            if v[3] == OceanMassMeasure.ANTARCTICA:
                antarctica_data.append(v)
            else:
                arctic_data.append(v)
        return arctic_data, antarctica_data


class RpcDatabaseEmissionDto:

    @staticmethod
    def normalize_data(data: list) -> dict:
        """
            Normalizes RpcDatabase data. To do so, values are separated according to the scenarios.
            Also, metadata such as the count of data, the start year and the end year are computed.
            :param data: A list of RpcDatabaseEmsision objects.
            :return: A `dict` containing the data described above.
        """
        if not data:
            return {}
        scenarios = RpcDatabaseEmission.get_scenarios_display()
        rpc_26 = []
        rpc_45 = []
        rpc_60 = []
        rpc_85 = []
        for v in data:
            if v[-1] == RpcDatabaseEmission.RPC_26:
                rpc_26.append(v[:-1])
            elif v[-1] == RpcDatabaseEmission.RPC_45:
                rpc_45.append(v[:-1])
            elif v[-1] == RpcDatabaseEmission.RPC_60:
                rpc_60.append(v[:-1])
            elif v[-1] == RpcDatabaseEmission.RPC_85:
                rpc_85.append(v[:-1])
        return {'data': ({'key': scenarios[1], 'values': rpc_26}, {'key': scenarios[2], 'values': rpc_45},
                         {'key': scenarios[3], 'values': rpc_60}, {'key': scenarios[4], 'values': rpc_85}),
                'total_data': len(data), 'start': rpc_26[0][0], 'end': rpc_26[-1][0]}


class CountryDto:

    def __init__(self, country, monitored_locations, monitored_location_id, population_data):
        """
            Initializes a CountryDto object. All of these fields can be obtained by invoking the CountryService.
            :param country: A Country object.
            :param monitored_locations: The amount of monitored locations.
            :param monitored_location_id: The ID of the monitored location, if the amount of monitored locations is 1.
            :param population_data: A `tuple`, containing data of the evolution of population for the country.
        """
        self.country = country
        self.monitored_locations = monitored_locations
        self.location_id = monitored_location_id
        self.population, self.population_year, self.population_previous, self.population_year_previous, self.percentage_difference = population_data
        self.i18n()

    def i18n(self):
        """
            This method encapsulates the internationalization of all translatable fields. These are:
                - Name of the Country.
                - Name of the Income level.
                - Name of the Country region.
        """
        self.country.name = _(self.country.name)
        self.country.income_level.name = _(self.country.income_level.name)
        self.country.region.name = _(self.country.region.name)


class CountryIndicatorDto:

    @staticmethod
    def normalize_data(measures: list) -> (int, int, int, dict):
        """
            Normalizes CountryIndicators' data.
            :param measures: A list of `tuple` objects. Each one contains the indicator ID, the value and the year.
            :return: A `tuple`, containing the amount of values, the first and last year, and a `dict` with all values.
        """
        if not measures:
            return 0, None, None, None, None, {}
        return len(measures), parse_date_utc(measures[0][0]).year, parse_date_utc(measures[-1][0]).year, {
            int(x[0] / 1000): x[1] for x in measures}

    @staticmethod
    def get_pollution_statistics_and_normalize_data(measures: list) -> dict:
        """
            Computes pollution statistics and normalizes data. Aggregates the sum of emissions, and the value for the
            last year. Also, metadata such as max, min and avg values are computed.
            :param measures: A list of CountryIndicator objects.
            :return: A `dict` containing all the stats.
        """
        if not measures:
            return {'data': [], 'stats': [None, None, None], 'total_data': 0, 'start_year': None, 'end_year': None}
        data = {'data': [(x.year, x.value) for x in measures], 'total_data': len(measures),
                'start_year': measures[0].year, 'end_year': measures[-1].year}
        stats = [None, None, 0, 0]
        for m in measures:
            if m.value > stats[0] if stats[0] is not None else True:
                stats[0] = m.value
            if m.value < stats[1] if stats[1] is not None else True:
                stats[1] = m.value
            stats[2] += 1
            stats[3] += m.value
        data['total_emissions'] = stats[3]
        data['last_year_emissions'] = measures[-1].value
        stats[3] = stats[3] / stats[2] if stats[2] > 0 else None
        data['stats'] = stats[:-1]
        return data

    @staticmethod
    def get_energy_statistics_and_normalize_data(measures: list, indicators: list) -> dict:
        """
            Computes energy statistics and normalizes data. Separates values by energy source, and the value for the
            last year. Also, metadata such as the first and last years are computed.
            :param measures: A list of CountryIndicator objects.
            :return: A `dict` containing all the stats.
        """
        if not measures:
            return {'data': None, 'total_data': 0, 'start_year': None, 'end_year': None}
        _values = {indicator: [] for indicator in indicators}
        data = {'data': None, 'total_data': len(measures), 'start_year': None, 'end_year': None, 'last_year_data': []}
        for m in measures:
            _values[m.indicator_id].append((m.year, m.value))
        data['data'] = list(_values.values())
        values = []
        for indicator in indicators:
            values.append(_values[indicator])
        data['start_year'] = min([l[0][0] for l in values if len(l) > 0])
        data['end_year'] = max([l[-1][0] for l in values if len(l) > 0])
        # Renewable energy should not be included in last year's data. Instead of it, computing the remaining
        # percentage, and substituting the value.
        data['last_year_data'] = [l[-1] for l in values[:-1] if len(l) > 0]
        # Last year data will only be available if all indicators have data, and all data belongs to the last year
        # (one or more values might be null for the last year, and subsequently not fetched from database)
        if len(data['last_year_data']) != len(indicators) - 1 or not all(
                [data['end_year'] == x[0] for x in data['last_year_data']]):
            data['last_year_data'] = None
        else:
            data['last_year_data'] = [x[1] for x in data['last_year_data']]
            data['last_year_data'].append(100 - sum(data['last_year_data']))
        return data

    @staticmethod
    def get_environment_statistics_and_normalize_data(measures: list, indicators: list, normalized_names) -> dict:
        """
            Computes environment statistics and normalizes data. Separates values by indicator. Also, metadata such as
            the first and last years are computed.
            :param measures: A list of CountryIndicator objects.
            :return: A `dict` containing all the stats.
        """
        if not measures:
            return {'data': None, 'total_data': 0}
        _values = {indicator: [] for indicator in indicators}
        data = {'data': None, 'total_data': len(measures)}
        for m in measures:
            _values[m.indicator_id].append((m.year, m.value))
        data['data'] = {}
        for index, l in enumerate(list(_values.values())):
            data['data'][normalized_names[index]] = {'start_year': None, 'end_year': None, 'end_year_data': None,
                                                     'data': None, 'count': 0} if len(l) == 0 else {
                'start_year': l[0][0], 'end_year': l[-1][0], 'end_year_data': l[-1][1], 'data': l, 'count': len(l)}
        return data
