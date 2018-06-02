from unittest import TestCase, mock
from unittest.mock import Mock

from pymongo.errors import DuplicateKeyError, OperationFailure

import utilities.mongo_util

collection = None
collection_name = 'test_collection'
database = 'test_database'
username = 'test_user'
password = 'test_password'
roles = [{"role": "dbOwner", "db": database}]


def get_collection(name=collection_name) -> utilities.mongo_util.MongoDBCollection:
    global collection
    if not collection or collection.is_closed():
        collection = utilities.mongo_util.MongoDBCollection(username=username, password=password, collection_name=name,
                                                            database=database, use_pool=False)
    collection.connect(name)
    return collection


class TestMongoUtil(TestCase):

    @classmethod
    def setUpClass(cls):
        import os
        if not os.environ.get('MONGODB_IP'):
            os.environ['MONGODB_IP'] = 'localhost'
        try:
            utilities.mongo_util.create_user(username, password, roles, database=database)
            utilities.mongo_util.create_user(username, password, roles, database='other_database')
        except DuplicateKeyError:
            pass

    def tearDown(self):
        get_collection().get_collection().drop()

    @classmethod
    def tearDownClass(cls):
        utilities.mongo_util.drop_user(username=username, database=database)
        utilities.mongo_util.drop_database(database=database)

    def test_close(self):
        self.assertFalse(get_collection().is_closed())
        get_collection().close()
        self.assertTrue(collection.is_closed())

    def test_connect(self):
        get_collection().connect('test_collection')
        self.assertEqual('test_collection', get_collection().get_collection().name)
        get_collection().connect('foo')
        self.assertEqual('foo', get_collection().get_collection().name)
        get_collection().close()

    def test_is_empty(self):
        self.assertTrue(get_collection().is_empty())
        get_collection().get_collection().insert_one({'_id': 1})
        self.assertFalse(get_collection().is_empty())

    def test_remove_all(self):
        from pymongo import InsertOne

        bulk_ops = []
        for index in range(1, 11):
            bulk_ops.append(InsertOne({'_id': index}))
        get_collection().get_collection().bulk_write(requests=bulk_ops)
        self.assertEqual(10, get_collection().get_collection().count())
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
        get_collection().get_collection().bulk_write(requests=bulk_ops)
        self.assertEqual(8, get_collection().get_collection().count())

        # Sorting only
        expected = sorted(values, key=lambda k: k['country_code'])
        data, next_start_index = get_collection().find(sort='country_code')
        self.assertListEqual(expected, data)

        # Sorting and paging
        expected = sorted(values, key=lambda k: k['_id'])
        data, next_start_index = get_collection().find(count=4, sort='_id')
        self.assertIsNotNone(next_start_index)
        data2, next_start_index2 = get_collection().find(start_index=next_start_index, sort='_id')
        self.assertListEqual(expected[:4], data)
        self.assertListEqual(expected[4:], data2)

        # Filtering
        expected = [values[6]]
        result = get_collection().find(conditions={'country_code': {'$eq': 'CN'}})[0]
        self.assertListEqual(expected, result)

        # Selecting fields
        expected = []
        for i in range(1, 9):
            expected.append({'_id': i})
        result = get_collection().find(fields={'_id': 1}, sort='_id')[0]
        self.assertListEqual(expected, result)

        # All combined
        expected = [{'_id': 1}, {'_id': 2}, {'_id': 4}, {'_id': 5}, {'_id': 7}, {'_id': 8}]
        data, next_start_index = get_collection().find(fields={'_id': 1}, count=4, sort='_id',
                                                       conditions={'latitude': {'$gt': 0}, 'longitude': {'$gt': 0}})
        self.assertIsNotNone(next_start_index)
        data2, next_start_index2 = get_collection().find(fields={'_id': 1}, sort='_id', start_index=next_start_index,
                                                         conditions={'latitude': {'$gt': 0}, 'longitude': {'$gt': 0}},
                                                         count=4)

        self.assertIsNone(next_start_index2)
        self.assertListEqual(expected[:4], data)
        self.assertListEqual(expected[4:], data2)

    def test_get_last_elements(self):
        self.assertIsNone(get_collection().get_last_elements())

        for i in range(1, 6):
            get_collection().get_collection().insert_one({'_id': i, 'data': 'DATA'})

        result = get_collection().get_last_elements()
        self.assertDictEqual({'_id': 5, 'data': 'DATA'}, result)

        result = get_collection().get_last_elements(amount=5)
        self.assertListEqual(get_collection().find()[0], result)

    def test_ping_database(self):
        self.assertIsNone(utilities.mongo_util.ping_database())

    @mock.patch('utilities.mongo_util.MongoClient')
    def test_ping_database_when_database_is_down(self, client):
        client.return_value.server_info = Mock(side_effect=EnvironmentError())
        with self.assertRaises(EnvironmentError):
            utilities.mongo_util.ping_database()
        self.assertTrue(client.called)

    def test_get_and_increment_execution_id(self):
        self.assertEqual(1, utilities.mongo_util.get_and_increment_execution_id(subsystem_id=1, database=database))
        self.assertEqual(2, utilities.mongo_util.get_and_increment_execution_id(subsystem_id=1, database=database))
        self.assertEqual(1, utilities.mongo_util.get_and_increment_execution_id(subsystem_id=2, database=database))

    def test_drop_database(self):
        c = get_collection()
        c.get_collection().insert_one({'_id': 1, 'data': 'foo'})
        res = c.find(conditions={'_id': 1})
        self.assertDictEqual({'_id': 1, 'data': 'foo'}, res[0][0])
        utilities.mongo_util.drop_database(database=database)
        res = c.find(conditions={'_id': 1})
        self.assertListEqual([], res[0])

    def test_create_user(self):
        try:
            with self.assertRaises(OperationFailure):
                collection = utilities.mongo_util.MongoDBCollection(collection_name, use_pool=False, username='user2',
                                                                    password='password2', database=database)
                collection.get_collection()
            utilities.mongo_util.create_user('user2', 'password2', [{"role": "read", "db": database}],
                                             database=database)
            c = utilities.mongo_util.MongoDBCollection(collection_name, use_pool=False, username='user2',
                                                       password='password2', database=database)
            self.assertListEqual([], c.find()[0])
        except AssertionError:
            raise
        finally:
            utilities.mongo_util.drop_user('user2', database)

    def test_drop_user(self):
        try:
            utilities.mongo_util.create_user('user2', 'password2', [{"role": "read", "db": database}],
                                             database=database)
            c = utilities.mongo_util.MongoDBCollection(collection_name, use_pool=False, username='user2',
                                                       password='password2', database=database)
            self.assertListEqual([], c.find()[0])
            self.assertTrue(utilities.mongo_util.drop_user('user2', database))
            with self.assertRaises(OperationFailure):
                c = utilities.mongo_util.MongoDBCollection(collection_name, use_pool=False, username='user2',
                                                           password='password2', database=database)
                c.get_collection()
        except AssertionError:
            raise
        finally:
            try:
                utilities.mongo_util.drop_user('user2', database)
            except:
                pass

    def test_bulk_create_authorized_users(self):
        from global_config.config import GLOBAL_CONFIG
        res = utilities.mongo_util.bulk_create_authorized_users(
                [{'_id': 'test_user', 'token': 'test_token', 'scope': 1},
                 {'_id': 'test_user2', 'token': 'test_token2', 'scope': 1},
                 {'_id': 'test_user3', 'token': 'test_token_with_no_scope', 'scope': None},
                 {'_id': 'test_user', 'token': 'gNJFSAI82', 'scope': 4}], database=database)
        self.assertEqual(4, res)
        c = get_collection(name=GLOBAL_CONFIG['MONGODB_API_AUTHORIZED_USERS_COLLECTION'])
        res = c.find()
        self.assertEqual([{'_id': 'test_user', 'token': 'test_token', 'scope': 1},
                          {'_id': 'test_user2', 'token': 'test_token2', 'scope': 1},
                          {'_id': 'test_user3', 'token': 'test_token_with_no_scope', 'scope': None}], res[0])

    def test_get_connection_pool(self):
        self.assertDictEqual({}, utilities.mongo_util.MongoDBCollection._pools)
        c = utilities.mongo_util.MongoDBCollection(collection_name=collection_name, use_pool=True, username=username,
                                                   password=password, database=database)
        c.get_collection()  # Initializes the actual collection
        self.assertNotEqual({}, utilities.mongo_util.MongoDBCollection._pools)
        self.assertEqual(1, len(utilities.mongo_util.MongoDBCollection._pools))
        self.assertIsNotNone(utilities.mongo_util.MongoDBCollection._pools.get(hash((username, database))))
        c2 = utilities.mongo_util.MongoDBCollection(collection_name=collection_name, use_pool=True, username=username,
                                                    password=password, database=database)
        c2.get_collection()
        self.assertIsNot(c, c2)
        self.assertIs(c._client, c2._client)
        c3 = utilities.mongo_util.MongoDBCollection(collection_name=collection_name, use_pool=True, username=username,
                                                    password=password, database='other_database')
        c3.get_collection()
        self.assertEqual(2, len(utilities.mongo_util.MongoDBCollection._pools))
        self.assertIsNot(c, c3)
        self.assertIsNot(c._client, c3._client)
        self.assertIsNotNone(utilities.mongo_util.MongoDBCollection._pools.get(hash((username, 'other_database'))))

    def test_proxy_collection(self):
        collection = utilities.mongo_util.MongoDBCollection(username=username, password=password, use_pool=False,
                                                            collection_name=collection_name, database=database)
        self.assertIsNone(collection._collection)
        self.assertIsNone(collection._client)
        collection.get_collection()  # This initializes the collection
        self.assertIsNotNone(collection._collection)
        self.assertIsNotNone(collection._client)
