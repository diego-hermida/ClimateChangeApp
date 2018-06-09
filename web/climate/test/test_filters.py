from climate.templatetags import filters
from django.test import SimpleTestCase


class RoundFilterTestCase(SimpleTestCase):

    def test_round(self):
        self.assertAlmostEqual(123.5, filters.round(123.5))

    def test_round_str(self):
        self.assertAlmostEqual(123.5, filters.round('123.5'))

    def test_round_greater_than_1000(self):
        self.assertAlmostEqual(1.2345, filters.round(1234.5))

    def test_round_greater_than_1000000(self):
        self.assertAlmostEqual(1.2345678, filters.round(1234567.8))

    def test_round_with_unparseable_content(self):
        self.assertEqual('?', filters.round('foo'))


class UnitsFilterTestCase(SimpleTestCase):

    def test_units(self):
        self.assertEqual('', filters.units(123.5))

    def test_units_str(self):
        self.assertEqual('', filters.units('123.5'))

    def test_units_greater_than_1000(self):
        self.assertEqual('K', filters.units(1234.5))

    def test_units_greater_than_1000000(self):
        self.assertEqual('M', filters.units(1234567.8))

    def test_units_with_unparseable_content(self):
        self.assertEqual('', filters.units('foo'))
