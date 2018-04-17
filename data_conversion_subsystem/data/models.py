from django.db import models
from django.contrib.postgres.fields import JSONField
from utilities.postgres_util import import_psycopg2

# This is required to work with PyPy.
import_psycopg2()


# Public enumerated types

MEASURE_UNITS = (
    ('MM', 'mm'),
    ('M', 'm'),
    ('M3', 'm³'),
    ('BM3', 'm³ (billions)'),
    ('PPM', 'ppm'),
    ('PPB', 'ppb'),
    ('PPT', 'ppb'),
    ('KT', 'kt'),
    ('T_PC', 't per capita'),
    ('GT', 'Gt'),
    ('KT_CO2EQ', 'kt CO₂eq'),
    ('CO2EQ_KWH', 'CO₂eq/kWh'),
    ('KWH', 'kW/h'),
    ('M_KWH', 'KW/h × 10⁶'),
    ('KWH_PC', 'kW/h (per capita)'),
    ('CELSIUS', '°C'),
    ('HPA', 'hPa'),
    ('KM_2', 'km²'),
    ('M_S', 'm/s'),
    ('KM_H', 'km/h'),
    ('PERCENT', '%'),
    ('PERCENT_LAND', '% (land area)'),
    ('PERCENT_SEA', '% (ocean area)'),
    ('PERCENT_TER', '% (territorial area)'),
    ('PERCENT_POP', '% (population with access)'),
    ('PERCENT_R_POP', '% (rural population with access)'),
    ('PERCENT_U_POP', '% (urban population with access)'),
    ('AQI', 'AQI'),
    ('DEGREES', '°')
)

WIND_DIRECTIONS = (
    ('N', 'N'),
    ('S', 'S'),
    ('W', 'W'),
    ('E', 'E'),
    ('NE', 'NE'),
    ('NW', 'NW'),
    ('SE', 'SE'),
    ('SW', 'SW'),
    ('NNE', 'NNE'),
    ('ENE', 'ENE'),
    ('ESE', 'ESE'),
    ('SSE', 'SSE'),
    ('SSW', 'SSW'),
    ('WSW', 'WSW'),
    ('WNW', 'WNW'),
    ('NNW', 'NNW'),
)


# Entities

class Region(models.Model):
    iso3_code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return 'Region [iso3_code (PK): %s, name: %s]' % (self.iso3_code, self.name)


class IncomeLevel(models.Model):
    iso3_code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return 'IncomeLevel [iso3_code (PK): %s, name: %s]' % (self.iso3_code, self.name)


class Country(models.Model):
    iso2_code = models.CharField(max_length=2, primary_key=True)
    iso3_code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=100, null=True)
    capital_city_name = models.CharField(max_length=100, null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)
    income_level = models.ForeignKey(IncomeLevel, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return 'Country [iso2_code (PK): %s, iso3_code: %s, name: %s, capital_city_name: %s, latitude: %s, ' \
               'longitude: %s, region (FK): %s, income_level (FK): %s]' % (self.iso2_code, self.iso3_code, self.name,
                self.capital_city_name, self.latitude, self.longitude, self.region, self.income_level)


class IndicatorDetails(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100, null=True)
    description = models.CharField(max_length=1000, null=True)
    units = models.CharField(max_length=14, choices=MEASURE_UNITS, null=True)
    type = models.CharField(max_length=100, null=True)
    attributions = models.CharField(max_length=500, null=True)

    def __str__(self):
        return 'IndicatorDetails [code (PK): %s, name: %s, description: %s, units: %s, type: %s, attributions: %s]' % (
                self.code, self.name, self.description, self.units, self.type, self.attributions)


class CountryIndicator(models.Model):
    indicator = models.ForeignKey(IndicatorDetails, on_delete=models.CASCADE, verbose_name='indicator details')
    country = models.ForeignKey(Country, on_delete=models.CASCADE, db_index=True)
    year = models.SmallIntegerField(db_index=True)
    value = models.FloatField(null=True)

    class Meta:
        unique_together = ('indicator', 'country', 'year')

    def __str__(self):
        return 'CountryIndicator [indicator (FK): %s, country (FK): %s, year: %s, value: %s]' % (self.indicator,
                self.country, self.year, self.value)


class EnergySourcesMeasure(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=False)
    timestamp = models.DateTimeField(db_index=True)
    carbon_intensity = models.FloatField(null=True)
    carbon_intensity_units = models.CharField(max_length=9, choices=MEASURE_UNITS, default='CO2EQ_KWH')
    fossil_fuel = models.FloatField(null=True)
    fossil_fuel_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='PERCENT')

    class Meta:
        unique_together = ('timestamp', 'country')

    def __str__(self):
        return 'EnergySourcesMeasure [country (FK): %s, timestamp: %s, carbon_intensity: %s, ' \
               'carbon_intensity_units: %s, fossil_fuel: %s, fossil_fuel_units: %s]' % (self.country, self.timestamp,
                self.carbon_intensity, self.carbon_intensity_units, self.fossil_fuel, self.fossil_fuel_units)


class Location(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True)
    name = models.CharField(max_length=100, db_index=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    climate_zone = models.CharField(max_length=3, db_index=True)
    elevation = models.SmallIntegerField(null=True)
    elevation_units = models.CharField(max_length=1, choices=MEASURE_UNITS, default=None, null=True)
    last_modified = models.DateTimeField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    population = models.BigIntegerField(null=True)
    owm_data = models.BooleanField(default=False)
    wunderground_data = models.BooleanField(default=False)
    air_pollution_data = models.BooleanField(default=False)
    timezone = models.CharField(max_length=30, null=True)
    air_pollution_attributions = JSONField(null=True, default=None)
    # Due to a circular reference between Location and AirPollutionMeasure, setting model as <str> instead of <object>
    air_pollution_last_measure = models.ForeignKey('data.AirPollutionMeasure', on_delete=models.SET_NULL, null=True,
                                                   related_name='+')

    def __str__(self):
        return 'Location [id (PK): %s, name: %s, country (FK): %s, climate_zone: %s, elevation: %s, ' \
               'elevation_units: %s, last_modified: %s, latitude: %s, longitude: %s, population: %s, ' \
               'owm_data: %s, wunderground_data: %s, air_pollution_data: %s, timezone: %s, ' \
               'air_pollution_last_measure: %s air_pollution_attributions: %s]' % (self.id, self.name, self.country,
                self.climate_zone, self.elevation, self.elevation_units, self.last_modified, self.latitude,
                self.longitude, self.population, self.owm_data,self.wunderground_data, self.air_pollution_data,
                self.timezone, self.air_pollution_last_measure, self.air_pollution_attributions)


class AirPollutionMeasure(models.Model):
    CO = 'CO'
    NO2 = 'NO2'
    O3 = 'O3'
    PM10 = 'PM10'
    PM25 = 'PM25'
    SO2 = 'SO2'
    POLLUTANT_TYPE = (
        (CO, 'CO'),
        (NO2, 'NO₂'),
        (O3, 'O₃'),
        (PM10, 'PM10'),
        (PM25, 'PM2.5'),
        (SO2, 'SO₂')
    )
    GREEN = 1
    YELLOW = 2
    ORANGE = 3
    RED = 4
    PURPLE = 5
    BROWN = 6
    COLOR_TYPE = (
        (GREEN, '#128a53'),
        (YELLOW, '#feda28'),
        (ORANGE, '#fd8627'),
        (RED, '#b30025'),
        (PURPLE, '#800080'),
        (BROWN, '#69001b')
    )
    TEXT_WHITE = 1
    TEXT_BLACK = 2
    TEXT_COLOR_TYPE = (
        (TEXT_WHITE, '#ffffff'),
        (TEXT_BLACK, '#000000')
    )
    TEXT_WHITE_COLORS = [GREEN, RED, PURPLE, BROWN]
    TEXT_BLACK_COLORS = [YELLOW, ORANGE]
    HEALTH_WARNING_LIMIT = 400.0

    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    dominant_pollutant = models.CharField(max_length=5, choices=POLLUTANT_TYPE, null=True)
    dominant_pollutant_value = models.FloatField(null=True)
    dominant_pollutant_color = models.PositiveSmallIntegerField(choices=COLOR_TYPE, null=True)
    dominant_pollutant_text_color = models.PositiveSmallIntegerField(choices=TEXT_COLOR_TYPE, null=True)
    timestamp = models.DateTimeField()
    timestamp_epoch = models.BigIntegerField(db_index=True)
    co_aqi = models.FloatField(null=True)
    co_aqi_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='AQI', null=True)
    no2_aqi = models.FloatField(null=True)
    no2_aqi_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='AQI', null=True)
    o3_aqi = models.FloatField(null=True)
    o3_aqi_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='AQI', null=True)
    pm25_aqi = models.PositiveSmallIntegerField(null=True)
    pm25_aqi_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='AQI', null=True)
    pm10_aqi = models.PositiveSmallIntegerField(null=True)
    pm10_aqi_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='AQI', null=True)
    so2_aqi = models.FloatField(null=True)
    so2_aqi_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='AQI', null=True)

    def display_health_warning(self) -> bool:
        return self.dominant_pollutant_value >= AirPollutionMeasure.HEALTH_WARNING_LIMIT \
            if self.dominant_pollutant_value else False

    def get_measures(self) -> list:
        co = {'name': AirPollutionMeasure.POLLUTANT_TYPE[0][1], 'value': self.co_aqi}
        no2 = {'name': AirPollutionMeasure.POLLUTANT_TYPE[1][1], 'value': self.no2_aqi}
        o3 = {'name': AirPollutionMeasure.POLLUTANT_TYPE[2][1], 'value': self.o3_aqi}
        pm10 = {'name': AirPollutionMeasure.POLLUTANT_TYPE[3][1], 'value': self.pm10_aqi}
        pm25 = {'name': AirPollutionMeasure.POLLUTANT_TYPE[4][1], 'value': self.pm25_aqi}
        so2 = {'name': AirPollutionMeasure.POLLUTANT_TYPE[5][1], 'value': self.so2_aqi}
        return [co, no2, o3, pm25, pm10, so2]

    def get_dominant_pollutant_value_display(self) -> float:
        if self.dominant_pollutant == AirPollutionMeasure.PM10 or self.dominant_pollutant == AirPollutionMeasure.PM25:
            return int(self.dominant_pollutant_value)
        else:
            return self.dominant_pollutant_value

    @staticmethod
    def get_pollutants_display() -> list:
        return [x[1] for x in AirPollutionMeasure.POLLUTANT_TYPE]

    @staticmethod
    def get_text_color(color: COLOR_TYPE, display=False):
        return (AirPollutionMeasure.TEXT_COLOR_TYPE[1][1] if display else AirPollutionMeasure.TEXT_BLACK) \
            if color in AirPollutionMeasure.TEXT_BLACK_COLORS else (AirPollutionMeasure.TEXT_COLOR_TYPE[0][1]
                if display else AirPollutionMeasure.TEXT_WHITE) if color is not None else None

    @staticmethod
    def get_color_list() -> list:
        return [{'color': x[1], 'text_color': AirPollutionMeasure.get_text_color(x[0], display=True)}
                for x in AirPollutionMeasure.COLOR_TYPE]

    @staticmethod
    def get_colors_display(value):
        color = AirPollutionMeasure.get_backgroud_color(value)
        return AirPollutionMeasure.get_backgroud_color(value, display=True), AirPollutionMeasure.get_text_color(
                color, display=True)

    @staticmethod
    def get_backgroud_color(value: float, display=False):
        if value is None:
            return None
        if 0.0 <= value <= 50.0:
            return AirPollutionMeasure.COLOR_TYPE[0][1] if display else AirPollutionMeasure.GREEN
        elif 50.0 < value <= 100.0:
            return AirPollutionMeasure.COLOR_TYPE[1][1] if display else AirPollutionMeasure.YELLOW
        elif 100.0 < value <= 150.0:
            return AirPollutionMeasure.COLOR_TYPE[2][1] if display else AirPollutionMeasure.ORANGE
        elif 150.0 < value <= 200.0:
            return AirPollutionMeasure.COLOR_TYPE[3][1] if display else AirPollutionMeasure.RED
        elif 200.0 < value <= 300.0:
            return AirPollutionMeasure.COLOR_TYPE[4][1] if display else AirPollutionMeasure.PURPLE
        elif value > 300.0:
            return AirPollutionMeasure.COLOR_TYPE[5][1] if display else AirPollutionMeasure.BROWN
        else:
            return None

    @staticmethod
    def get_dominant_pollutant_values(dominant_pollutant: str, values: dict) -> (float, int, int):
        if dominant_pollutant is None:
            return None, None, None
        value = values.get(dominant_pollutant)
        color = AirPollutionMeasure.get_backgroud_color(value)
        return value, color, AirPollutionMeasure.get_text_color(color)

    class Meta:
        unique_together = ('location', 'timestamp')

    def __str__(self):
        return 'AirPollutionMeasure [location (FK): %d, dominant_pollutant: %s, timestamp: %s, co_aqi: %s, ' \
               'co_aqi_units: %s, no2_aqi: %s, no2_aqi_units: %s, o3_aqi: %s, o3_aqi_units: %s, pm25_aqi: %s,'\
               'pm25_aqi_units: %s, pm10_aqi: %s, pm10_aqi_units: %s, so2_aqi: %s, so2_aqi_units: %s]' % (
                self.location_id, self.dominant_pollutant, self.timestamp, self.co_aqi, self.co_aqi_units, self.no2_aqi,
                self.no2_aqi_units, self.o3_aqi, self.o3_aqi_units, self.pm25_aqi, self.pm25_aqi_units, self.pm10_aqi,
                self.pm10_aqi_units, self.so2_aqi, self.so2_aqi_units)


class WeatherType(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    icon_code = models.CharField(max_length=16, null=True)
    description = models.CharField(max_length=60, null=True)

    def __str__(self):
        return 'WeatherType [id (PK): %s, icon_code: %s, description: %s]' % (self.id, self.icon_code, self.description)


class CurrentConditionsObservation(models.Model):
    location = models.OneToOneField(Location, on_delete=models.CASCADE, primary_key=True)
    timestamp = models.DateTimeField(db_index=True)
    temperature = models.SmallIntegerField(null=True)
    temperature_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='CELSIUS', null=True)
    pressure = models.SmallIntegerField(null=True)
    pressure_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='HPA', null=True)
    humidity = models.PositiveSmallIntegerField(null=True)
    humidity_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='PERCENT', null=True)
    wind_speed = models.PositiveSmallIntegerField(null=True)
    wind_speed_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='M_S', null=True)
    wind_degrees = models.PositiveSmallIntegerField(null=True)
    wind_degrees_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='DEGREES', null=True)
    wind_direction = models.CharField(max_length=3, choices=WIND_DIRECTIONS, null=True)
    sunrise = models.DateTimeField(null=True)
    sunset = models.DateTimeField(null=True)
    weather = models.ForeignKey(WeatherType, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return 'CurrentConditionsObservation [location (FK): %s, timestamp: %s, temperature: %s, temperature_units:'\
               ' %s, pressure: %s, pressure_units: %s, humidity: %s, pressure_units: %s, wind_speed: %s, ' \
               'wind_speed_units: %s, wind_degrees: %s, wind_degrees_units: %s, wind_direction: %s, sunrise: %s, ' \
               'sunset: %s, weather (FK): %s]' % (self.location, self.timestamp, self.temperature,
                self.temperature_units, self.pressure, self.pressure_units, self.humidity, self.humidity_units,
                self.wind_speed, self.wind_speed_units, self.wind_degrees, self.wind_degrees_units, self.wind_direction,
                self.sunrise, self.sunset, self.weather)


class WeatherForecastObservation(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    time = models.TimeField(db_index=True)
    temperature = models.SmallIntegerField(null=True)
    temperature_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='CELSIUS', null=True)
    pressure = models.SmallIntegerField(null=True)
    pressure_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='HPA', null=True)
    humidity = models.PositiveSmallIntegerField(null=True)
    humidity_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='PERCENT', null=True)
    wind_speed = models.PositiveSmallIntegerField(null=True)
    wind_speed_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='M_S', null=True)
    wind_degrees = models.PositiveSmallIntegerField(null=True)
    wind_degrees_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='DEGREES', null=True)
    wind_direction = models.CharField(max_length=3, choices=WIND_DIRECTIONS, null=True)
    sunrise = models.DateTimeField(null=True)
    sunset = models.DateTimeField(null=True)
    weather = models.ForeignKey(WeatherType, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('location', 'date', 'time')

    def __str__(self):
        return 'WeatherForecastObservation [location (FK): %s, date: %s, time: %s, temperature: %s, temperature_units:'\
               ' %s, pressure: %s, pressure_units: %s, humidity: %s, pressure_units: %s, wind_speed: %s, ' \
               'wind_speed_units: %s, wind_degrees: %s, wind_degrees_units: %s, wind_direction: %s, sunrise: %s, ' \
               'sunset: %s, weather (FK): %s]' % (self.location, self.date, self.time, self.temperature,
                self.temperature_units, self.pressure, self.pressure_units, self.humidity, self.humidity_units,
                self.wind_speed, self.wind_speed_units, self.wind_degrees, self.wind_degrees_units, self.wind_direction,
                self.sunrise, self.sunset, self.weather)


class HistoricalWeatherObservation(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    date = models.DateField()
    date_epoch = models.BigIntegerField(db_index=True)
    year = models.PositiveSmallIntegerField(db_index=True)
    fog = models.NullBooleanField()
    rain = models.NullBooleanField()
    snow = models.NullBooleanField()
    hail = models.NullBooleanField()
    thunder = models.NullBooleanField()
    tornado = models.NullBooleanField()
    snow_fall = models.FloatField(null=True)
    snow_fall_units = models.CharField(max_length=2, choices=MEASURE_UNITS, default='MM', null=True)
    snow_depth = models.FloatField(null=True)
    snow_depth_units = models.CharField(max_length=2, choices=MEASURE_UNITS, default='MM', null=True)
    mean_temp = models.SmallIntegerField(null=True)
    mean_temp_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='CELSIUS', null=True)
    mean_pressure = models.FloatField(null=True)
    mean_pressure_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='HPA', null=True)
    mean_wind_speed = models.SmallIntegerField(null=True)
    mean_wind_speed_units = models.CharField(max_length=4, choices=MEASURE_UNITS, default='KM_H', null=True)
    mean_wind_direction = models.CharField(max_length=3, choices=WIND_DIRECTIONS, null=True)
    mean_wind_direction_degrees = models.SmallIntegerField(null=True)
    mean_wind_direction_degrees_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='DEGREES',
                                                         null=True)
    humidity = models.SmallIntegerField(null=True)
    humidity_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='PERCENT', null=True)
    max_temp = models.SmallIntegerField(null=True)
    max_temp_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='CELSIUS', null=True)
    max_pressure = models.FloatField(null=True)
    max_pressure_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='HPA', null=True)
    max_wind_speed = models.SmallIntegerField(null=True)
    max_wind_speed_units = models.CharField(max_length=4, choices=MEASURE_UNITS, default='KM_H', null=True)
    min_temp = models.SmallIntegerField(null=True)
    min_temp_units = models.CharField(max_length=7, choices=MEASURE_UNITS, default='CELSIUS', null=True)
    min_pressure = models.FloatField(null=True)
    min_pressure_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='HPA', null=True)
    min_wind_speed = models.SmallIntegerField(null=True)
    min_wind_speed_units = models.CharField(max_length=4, choices=MEASURE_UNITS, default='KM_H', null=True)
    precipitation = models.FloatField(null=True)
    precipitation_units = models.CharField(max_length=2, choices=MEASURE_UNITS, default='MM', null=True)

    class Meta:
        unique_together = ('location', 'date')

    def __str__(self):
        return 'HistoricalWeatherObservation [location (FK): %s, date: %s]' % (self.location, self.date)


class SeaLevelRiseMeasure(models.Model):
    SINGLE_FREQUENCY = 'SF'
    DUAL_FREQUENCY = 'DF'
    ALTIMETER_TYPE = (
        ('SF', 'Single Frequency'),
        ('DF', 'Dual Frequency')
    )
    timestamp_epoch = models.BigIntegerField(primary_key=True, auto_created=False)
    year = models.PositiveSmallIntegerField()
    altimeter = models.CharField(max_length=2, choices=ALTIMETER_TYPE)
    units = models.CharField(max_length=2, choices=MEASURE_UNITS, default='MM')
    variation = models.FloatField()
    deviation = models.FloatField()
    smoothed_variation = models.FloatField()
    variation_GIA = models.FloatField()
    deviation_GIA = models.FloatField()
    smoothed_variation_GIA = models.FloatField()
    smoothed_variation_GIA_annual_semi_annual_removed = models.FloatField()

    def __str__(self):
        return 'SeaLevelRiseMeasure [timestamp: %s, altimeter: %s, units: %s, variation: %s, deviation: %s, ' \
               'smoothed_variation: %s, variation_GIA: %s, deviation_GIA: %s, smoothed_variation_GIA: %s,'\
               'smoothed_variation_GIA_annual_semi_annual_removed: %s]' % (self.timestamp, self.altimeter, self.units,
                self.variation, self.deviation, self.smoothed_variation, self.variation_GIA, self.deviation_GIA,
                self.smoothed_variation_GIA, self.smoothed_variation_GIA_annual_semi_annual_removed)


class OceanMassMeasure(models.Model):
    ANTARCTICA = 'ANT'
    GREENLAND = 'GRE'
    OCEAN = 'OCE'
    OCEAN_MASS_MEASURE_TYPE = (
        ('ANT', 'Antarctica'),
        ('GRE', 'Greenland'),
    )
    timestamp_epoch = models.BigIntegerField(db_index=True)
    year = models.PositiveSmallIntegerField()
    type = models.CharField(max_length=3, choices=OCEAN_MASS_MEASURE_TYPE)
    mass = models.FloatField(null=True)
    mass_units = models.CharField(max_length=2, choices=MEASURE_UNITS, default='GT', null=True)
    uncertainty = models.FloatField(null=True)
    uncertainty_units = models.CharField(max_length=2, choices=MEASURE_UNITS, default='GT', null=True)
    trend = models.FloatField(null=True)
    trend_units = models.CharField(max_length=2, choices=MEASURE_UNITS, default='GT', null=True)

    class Meta:
        unique_together = ('timestamp_epoch', 'type')

    def __str__(self):
        return 'OceanMassMeasure [timestamp: %s, type: %s, mass: %s, mass_units: %s, uncertainty: %s, ' \
               'uncertainty_units: %s, trend: %s]' % (self.timestamp_epoch, self.type, self.mass, self.mass_units,
                self.uncertainty, self.uncertainty_units, self.trend)


class RpcDatabaseEmission(models.Model):
    PRE_2005 = 'PRE_2005'
    RPC_26 = 'RPC_26'
    RPC_45 = 'RPC_45'
    RPC_60 = 'RPC_60'
    RPC_85 = 'RPC_85'
    SCENARIO_TYPE = (
        ('PRE_2005', 'Before 2005'),
        ('RPC_26', 'RPC 2.6'),
        ('RPC_45', 'RPC 4.5'),
        ('RPC_60', 'RPC 6.0'),
        ('RPC_85', 'RPC 8.5')
    )
    year = models.SmallIntegerField(db_index=True)
    scenario = models.CharField(max_length=8, choices=SCENARIO_TYPE, db_index=True)
    co2_eq = models.FloatField()
    co2_eq_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPM')
    kyoto_co2_eq = models.FloatField()
    kyoto_co2_eq_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPM')
    co2 = models.FloatField()
    co2_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPM')
    ch4 = models.FloatField()
    ch4_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPB')
    n2o = models.FloatField()
    n2o_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPB')
    kyoto_flourinated_hfc134a_eq = models.FloatField()
    kyoto_flourinated_hfc134a_eq_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    montreal_flourinated_cfc_13_eq = models.FloatField()
    montreal_flourinated_cfc_13_eq_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    cf4 = models.FloatField()
    cf4_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    c2f6 = models.FloatField()
    c2f6_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    c6f14 = models.FloatField()
    c6f14_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hfc23 = models.FloatField()
    hfc23_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hfc32 = models.FloatField()
    hfc32_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hfc43_10 = models.FloatField()
    hfc43_10_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hfc125 = models.FloatField()
    hfc125_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hfc134a = models.FloatField()
    hfc134a_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hfc143a = models.FloatField()
    hfc143a_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hfc227ea = models.FloatField()
    hfc227ea_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hfc245fa = models.FloatField()
    hfc245fa_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    sf6 = models.FloatField()
    sf6_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    cfc_11 = models.FloatField()
    cfc_11_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    cfc_12 = models.FloatField()
    cfc_12_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    cfc_113 = models.FloatField()
    cfc_113_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    cfc_114 = models.FloatField()
    cfc_114_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    cfc_115 = models.FloatField()
    cfc_115_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    carb_tet = models.FloatField()
    carb_tet_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    mfc = models.FloatField()
    mfc_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hcfc_22 = models.FloatField()
    hcfc_22_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hcfc_141b = models.FloatField()
    hcfc_141b_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    hcfc_142b = models.FloatField()
    hcfc_142b_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    halon_1211 = models.FloatField()
    halon_1211_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    halon_1202 = models.FloatField()
    halon_1202_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    halon_1301 = models.FloatField()
    halon_1301_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    halon_2402 = models.FloatField()
    halon_2402_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    ch3br = models.FloatField()
    ch3br_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')
    ch3cl = models.FloatField()
    ch3cl_units = models.CharField(max_length=3, choices=MEASURE_UNITS, default='PPT')

    class Meta:
        indexes = [models.Index(fields=['year', 'scenario'])]
        unique_together = ('year', 'scenario')

    def __str__(self):
        return 'RpcDatabaseEmission [year: %s, scenario: %s]' % (self.year, self.scenario)


# Statistics and metadata

class ExecutionStatistics(models.Model):
    subsystem_id = models.PositiveSmallIntegerField(auto_created=False)
    execution_id = models.BigIntegerField()
    data = JSONField(null=False)

    class Meta:
        # Last execution reports are more likely to be selected. Creating index (subsystem_id, execution_id DESC).
        indexes = [models.Index(fields=['subsystem_id', '-execution_id'], name='stats_index_on_subs_id_exec_id')]
        unique_together = ('subsystem_id', 'execution_id')

    def __str__(self):
        return 'ExecutionStatistics [subsystem_id: %s, execution_id: %s, data: %s]' % (self.subsystem_id,
                self.execution_id, self.data)


class AggregatedStatistics(models.Model):
    subsystem_id = models.PositiveSmallIntegerField(auto_created=False, primary_key=True)
    data = JSONField(null=False)

    def __str__(self):
        return 'AggregatedStatistics [subsystem_id: %s, data: %s]' % (self.subsystem_id, self.data)


class ExecutionId(models.Model):
    subsystem_id = models.PositiveSmallIntegerField(primary_key=True, auto_created=False)
    # It's necessary to override the "save" operation in order to get a non-primary key auto-increment field in Django.
    execution_id = models.BigIntegerField(default=1)

    def save(self, *args, **kwargs):
        # Get the maximum display_id value from the database
        last_id = ExecutionId.objects.all().aggregate(largest=models.Max('execution_id'))['largest']
        # aggregate can return None! Check it first.
        # If it isn't none, just use the last ID specified (which should be the greatest) and add one to it
        if last_id is not None:
            self.execution_id = last_id + 1
        super(ExecutionId, self).save(*args, **kwargs)

    def __str__(self):
        return 'ExecutionId [subsystem_id: %s, execution_id: %s]' % (self.subsystem_id, self.execution_id)
