from os import environ
from pymongo import MongoClient

from utilities.util import get_config


def drop_application_database():
    """
        Deletes all contents from the Subsystem database.
    """
    config = get_config(__file__)
    MongoClient(host=environ.get(config['DB_SERVER'], 'localhost'),
                port=config['DB_PORT'],
                authSource=config['DB_ADMIN'],
                serverSelectionTimeoutMS=config['DB_MAX_MILLISECONDS_WAIT'],
                username=config['DB_ROOT'],
                password=config['DB_ROOT_PASSWORD'],
                authMechanism=config['DB_AUTH_MECHANISM']).drop_database(config['DATABASE'])


def create_application_user():
    """
        Creates an admin user, who owns the Subsystem database on MongoDB.
        If the database does not exist, it will also be created.
    """
    config = get_config(__file__)
    MongoClient(host=environ.get(config['DB_SERVER'], 'localhost'),
                port=config['DB_PORT'],
                authSource=config['DB_ADMIN'],
                serverSelectionTimeoutMS=config['DB_MAX_MILLISECONDS_WAIT'],
                username=config['DB_ROOT'], password=config['DB_ROOT_PASSWORD'],
                authMechanism=config['DB_AUTH_MECHANISM']).get_database(config['DATABASE']).command('createUser',
        config['DB_USERNAME'], pwd=config['DB_PASSWORD'], roles=[{"role" : "dbOwner", "db" : "climatechange"}])


class MongoDBCollection:
    """
        This class acts as an abstraction to a MongoDB Collection. It provides a wrapper interface for some operations,
        such as initialization and closure of connections, search operations...
    """
    def __init__(self, collection_name):
        """
            Initializes a collection to perform database operations. The actual PyMongo collection is the only exposed
            attribute, in order to perform all its operations.
            Instantiation will fail if the database is down, since the connection is validated at this point.
            Postcondition: A valid connection with the collection has been established.
            :param collection_name: Name of the collection to be connected to.
        """
        self.__collection_name = collection_name
        self.__config = get_config(__file__)
        self.__client = MongoClient(
            host=environ.get(self.__config['DB_SERVER'], 'localhost'),
            port=self.__config['DB_PORT'],
            authSource=self.__config['DATABASE'],
            serverSelectionTimeoutMS=self.__config['DB_MAX_MILLISECONDS_WAIT'],
            username=self.__config['DB_USERNAME'],
            password=self.__config['DB_PASSWORD'],
            authMechanism=self.__config['DB_AUTH_MECHANISM'])
        self.__client.server_info()  # Checks valid connection.
        self.collection = self.__client.get_database(self.__config['DATABASE']).get_collection(collection_name)

    def is_closed(self) -> bool:
        """
            Checks whether or not the current connection to the collection is closed.
            :return: True, if the either the client or the connection are None, False otherwise.
        """
        return self.collection is None or self.__client is None

    def close(self):
        """
            Closes the MongoClient, and unassigns the 'collection' variable.
            However, the MongoDBCollection instance can still be used, by calling the 'connect' method first, which will
            open the connection and initialize the collection again.
        """
        self.__client.close()  # If used later, MongoClient will automatically open the connection with MongoDB
        self.collection = None

    def connect(self, collection_name=None):
        """
            Performs a connection attempt to a collection. If the connection to the previous collection is still open,
            it will be closed before initializing the new one.
            :param collection_name: Name of the collection to be connected to. If this name is the same as the current
                                    collection, this operation won't do anything.
        """
        if self.__collection_name == collection_name:
            return
        if not self.is_closed():
            self.close()
        self.collection = self.__client.get_database(self.__config['DATABASE']).get_collection(
            collection_name if collection_name else self.__collection_name)

    def find(self, fields=None, conditions=None, last_id=None, count=None, sort=None) -> dict:
        """
            Searches for data in a MongoDB collection. Results are paged (if 'count' and 'last_id' are set).
            :param fields: Fields to be selected. Any field to be selected is tagged with a '1'. Any field to be exclu-
                           ded is tagged with a '0'. '1's and '0's cannot be combined. Examples:
                                - db.<table>.find({'_id': 1, 'name': 1}) --> SELECT _id, name FROM <table>
                                - db.<table>.find({'_id': 0}) --> SELECT <all fields but '_id' field> FROM <table>
            :param conditions: Conditions that data must met to be selected. If "conditions" = None, a default condition
                               is imposed if 'last_id' isn't None: '_id' field must be greater than 'last_id'.
            :param last_id: Data will be retrieved from 'last_id' action value (or from the beginning if last_id is None)
            :param count: Sets a maximum amount of values returned per __transition_state call (no limit if count is None).
            :param sort: If not specified, uses a $natural sort. Otherwise, 'sort' can be a single string (sorts by the
                         field with that name, ascending), or a list of tuples with the following format:
                         [(field_1, <1 or -1>), ..., (field_N,  <1 or -1>)]. Examples:
                                - db.<table>.find().sort('name') --> SELECT * FROM <table> ORDER BY 'name'
                                - db.<table>.find().sort([('name', 1), ('price', -1)]) --> SELECT * FROM <table>
                                                                                           ORDER BY 'name', 'price' DESC
            :return: A dict with two values:
                        - data: A list of values, or None if there were not values.
                        - more: A bool value, indicating whether retrieved data is the last or not.
            :rtype: dict
        """
        if last_id:
            if not conditions:
                conditions = {}
            conditions['_id'] = {'$gt': last_id}
        cursor = self.collection.find(conditions, fields).sort(sort if sort else '$natural'). \
            limit(count + 1 if count else 0)
        data = [x for x in cursor]
        cursor.close()
        data = {'data': data if data else [], 'more': len(data) > count if count else False}
        if data['more']:
            # Discarding last element (necessary to determine if there are more elements, but not requested)
            data['data'] = data['data'][:-1]
        return data

    def is_empty(self) -> bool:
        """
        Checks whether a collection is empty or not.
        :return: True if the collection is empty, False otherwise.
        :rtype: bool
        """
        return self.collection.count() == 0

    def remove_all(self):
        """
        Removes all elements from the collection.
        """
        return self.collection.delete_many({})
