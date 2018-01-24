from unittest import TestCase, main, mock

import utilities.db_util

collection = None


def get_collection() -> utilities.db_util.MongoDBCollection:
    global collection
    if not collection or collection.is_closed():
        collection = utilities.db_util.MongoDBCollection('test_collection')
    return collection


class TestDbUtil(TestCase):

    def tearDown(self):
        get_collection().remove_all()

    @classmethod
    def tearDownClass(cls):
        if get_collection():
            get_collection().collection.drop()

    def test_close(self):
        self.assertFalse(get_collection().is_closed())
        get_collection().close()
        self.assertTrue(collection.is_closed())

    def test_connect(self):
        get_collection().connect('test_collection')
        self.assertEqual('test_collection', get_collection().collection.name)
        get_collection().connect('foo')
        self.assertEqual('foo', get_collection().collection.name)
        get_collection().close()

    def test_is_empty(self):
        self.assertTrue(get_collection().is_empty())
        get_collection().collection.insert_one({'_id': 1})
        self.assertFalse(get_collection().is_empty())

    def test_remove_all(self):
        from pymongo import InsertOne

        bulk_ops = []
        for index in range(1, 11):
            bulk_ops.append(InsertOne({'_id': index}))
        get_collection().collection.bulk_write(requests=bulk_ops)
        self.assertEqual(10, get_collection().collection.count())
        self.assertFalse(get_collection().is_empty())
        get_collection().remove_all()
        self.assertTrue(get_collection().is_empty())

    def test_find(self):
        from pymongo import InsertOne

        values = [{'_id': 1, 'country_code': 'EG', 'latitude': 30.06263, 'longitude': 31.24967},
                  {'_id': 2, 'country_code': 'IN', 'latitude': 28.65195, 'longitude': 77.23149},
                  {'_id': 3, 'country_code': 'MX', 'latitude': 19.42847, 'longitude': -99.12766},
                  {'_id': 4, 'country_code': 'TH', 'latitude': 13.75398, 'longitude': 100.50144},
                  {'_id': 5, 'country_code': 'TR', 'latitude': 39.91987, 'longitude': 32.85427},
                  {'_id': 6, 'country_code': 'ES', 'latitude': 40.4165, 'longitude': -3.70256},
                  {'_id': 7, 'country_code': 'CN', 'latitude': 39.9075, 'longitude': 116.39723},
                  {'_id': 8, 'country_code': 'ES', 'latitude': 41.38879, 'longitude': 2.15899}]

        bulk_ops = []
        for value in values:
            bulk_ops.append(InsertOne(value))
        get_collection().collection.bulk_write(requests=bulk_ops)
        self.assertEqual(8, get_collection().collection.count())

        # Sorting only
        expected = sorted(values, key=lambda k: k['country_code'])
        result = get_collection().find(sort='country_code')['data']
        self.assertListEqual(expected, result)

        # Sorting and paging
        expected = sorted(values, key=lambda k: k['_id'])
        first_page = get_collection().find(count=4, sort='_id')
        self.assertTrue(first_page['more'])
        last_page = get_collection().find(last_id=first_page['data'][-1]['_id'], sort='_id')
        self.assertListEqual(expected[:4], first_page['data'])
        self.assertListEqual(expected[4:], last_page['data'])

        # Filtering
        expected = [values[6]]
        result = get_collection().find(conditions={'country_code': {'$eq': 'CN'}})['data']
        self.assertListEqual(expected, result)

        # Selecting fields
        expected = []
        for i in range(1, 9):
            expected.append({'_id': i})
        result = get_collection().find(fields={'_id': 1}, sort='_id')['data']
        self.assertListEqual(expected, result)

        # All combined
        expected = [{'_id': 1}, {'_id': 2}, {'_id': 4}, {'_id': 5}, {'_id': 7}, {'_id': 8}]
        first_page = get_collection().find(fields={'_id': 1}, count=4, sort='_id',
                                           conditions={'latitude': {'$gt': 0}, 'longitude': {'$gt': 0}})
        self.assertTrue(first_page['more'])
        last_page = get_collection().find(fields={'_id': 1}, sort='_id', last_id=first_page['data'][-1]['_id'],
                                          conditions={'latitude': {'$gt': 0}, 'longitude': {'$gt': 0}}, count=4)

        self.assertFalse(last_page['more'])
        self.assertListEqual(expected[:4], first_page['data'])
        self.assertListEqual(expected[4:], last_page['data'])

    def test_get_last_elements(self):
        for i in range(1, 6):
            get_collection().collection.insert_one({'_id': i, 'data': 'DATA'})

        result = get_collection().get_last_elements()
        self.assertDictEqual({'_id': 5, 'data': 'DATA'}, result)

        result = get_collection().get_last_elements(amount=5)
        self.assertListEqual(get_collection().find()['data'], result)
