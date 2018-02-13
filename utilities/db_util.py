from global_config.global_config import GLOBAL_CONFIG
from os import environ
from pymongo import MongoClient


def drop_application_database():
    """
        Deletes all contents from the Subsystem database.
    """
    MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'),
                port=GLOBAL_CONFIG['MONGODB_PORT'],
                authSource=GLOBAL_CONFIG['MONGODB_ADMIN'],
                serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                username=GLOBAL_CONFIG['MONGODB_ROOT'],
                password=GLOBAL_CONFIG['MONGODB_ROOT_PASSWORD'],
                authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM']).drop_database(GLOBAL_CONFIG['MONGODB_DATABASE'])


def create_application_user():
    """
        Creates an admin user, who owns the Subsystem database on MongoDB.
    """
    MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'),
                port=GLOBAL_CONFIG['MONGODB_PORT'],
                authSource=GLOBAL_CONFIG['MONGODB_ADMIN'],
                serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                username=GLOBAL_CONFIG['MONGODB_ROOT'], password=GLOBAL_CONFIG['MONGODB_ROOT_PASSWORD'],
                authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM']).get_database(GLOBAL_CONFIG['MONGODB_DATABASE']).\
        command('createUser', GLOBAL_CONFIG['MONGODB_USERNAME'], pwd=GLOBAL_CONFIG['MONGODB_PASSWORD'], roles=[{"role":
                "dbOwner", "db": GLOBAL_CONFIG['MONGODB_DATABASE']}])


def drop_application_user():
    """
        Drops the admin user, who owns the Subsystem database on MongoDB.
    """
    MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'),
                port=GLOBAL_CONFIG['MONGODB_PORT'],
                authSource=GLOBAL_CONFIG['MONGODB_ADMIN'],
                serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                username=GLOBAL_CONFIG['MONGODB_ROOT'], password=GLOBAL_CONFIG['MONGODB_ROOT_PASSWORD'],
                authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM']).get_database(GLOBAL_CONFIG['MONGODB_DATABASE']).\
        command('dropUser', GLOBAL_CONFIG['MONGODB_USERNAME'])


def create_authorized_user(username: str, token: str, scope: int):
    """
        Creates an authorized user, granting him/her access to the Subsystem API.
    """
    c = MongoDBCollection(collection_name=GLOBAL_CONFIG['MONGODB_API_AUTHORIZED_USERS_COLLECTION'])
    c.collection.update_one({'_id': username}, {'$setOnInsert': {'_id': username, 'token': token, 'scope': scope}},
            upsert=True)


def bulk_create_authorized_users(users: list) -> int:
    """
        Creates N authorized users, given a list of users.
        If an user was already authorized, this operation updates its data, just in case its token has been modified.
        :param users: List of users. Each user must be a JSON serializable object, with the following structure:
                                          {'_id': <username>, 'token': <token>}
        :return: The number of successfully upserted users.
    """
    from pymongo import UpdateOne
    ops = []
    for user in users:
        ops.append(UpdateOne({'_id': user['_id']}, update={'$set': user}, upsert=True))
    c = MongoDBCollection(collection_name=GLOBAL_CONFIG['MONGODB_API_AUTHORIZED_USERS_COLLECTION'])
    result = c.collection.bulk_write(ops)
    return result.bulk_api_result['nInserted'] + result.bulk_api_result['nMatched'] + result.bulk_api_result['nUpserted']


def ping_database():
    """
        Performs a connection attempt, to ensure database is up. Regardless of the error, the client will be closed.
        :raises EnvironmentError: If any error occurs during the process.
    """
    client = None
    try:
        client = MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'), port=GLOBAL_CONFIG[
            'MONGODB_PORT'], authSource=GLOBAL_CONFIG['MONGODB_ADMIN'], serverSelectionTimeoutMS=GLOBAL_CONFIG[
            'MONGODB_DB_MAX_MILLISECONDS_WAIT'], username=GLOBAL_CONFIG['MONGODB_ROOT'], password=GLOBAL_CONFIG[
            'MONGODB_ROOT_PASSWORD'], authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM'])
        client.server_info()
    except Exception as exc:
        raise EnvironmentError from exc
    finally:
        try:
            if client is not None:
                client.close()
        except:
            pass


def get_and_increment_execution_id() -> int:
    """
        Retrieves the current execution ID. Each time this value is retrieved, it is auto-incremented in one unit.
        Postcondition: The execution ID is auto-incremented in one unit.
        :return: An integer, containing the current execution ID.
    """
    from data_gathering_subsystem.config.config import DGS_CONFIG
    collection = MongoDBCollection(GLOBAL_CONFIG['MONGODB_STATS_COLLECTION'])
    return collection.collection.find_and_modify(query={'_id': {'execution_id': True, 'subsystem_id': DGS_CONFIG[
        'SUBSYSTEM_INSTANCE_ID']}}, update={'$inc': {'value': 1}}, fields={'value': 1}, new=True, upsert=True)['value']


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
        self._collection_name = collection_name
        self._client = MongoClient(
            host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'),
            port=GLOBAL_CONFIG['MONGODB_PORT'],
            authSource=GLOBAL_CONFIG['MONGODB_DATABASE'],
            serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
            username=GLOBAL_CONFIG['MONGODB_USERNAME'],
            password=GLOBAL_CONFIG['MONGODB_PASSWORD'],
            authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM'])
        self._client.server_info()  # Checks valid connection.
        self.collection = self._client.get_database(GLOBAL_CONFIG['MONGODB_DATABASE']).get_collection(collection_name)

    def is_closed(self) -> bool:
        """
            Checks whether or not the current connection to the collection is closed.
            :return: True, if the either the client or the connection are None, False otherwise.
        """
        return self.collection is None or self._client is None

    def close(self):
        """
            Closes the MongoClient, and unassigns the 'collection' variable.
            However, the MongoDBCollection instance can still be used, by calling the 'connect' method first, which will
            open the connection and initialize the collection again.
        """
        self._client.close()  # If used later, MongoClient will automatically open the connection with MongoDB
        self.collection = None

    def connect(self, collection_name=None):
        """
            Performs a connection attempt to a collection. If the connection to the previous collection is still open,
            it will be closed before initializing the new one.
            :param collection_name: Name of the collection to be connected to. If this name is the same as the current
                                    collection, this operation won't do anything.
        """
        if self._collection_name == collection_name and not self.is_closed():
            return
        elif self._collection_name != collection_name:
            self.close()
        self.collection = self._client.get_database(GLOBAL_CONFIG['MONGODB_DATABASE']).get_collection(
            collection_name if collection_name else self._collection_name)

    def find(self, fields=None, conditions={}, start_index=None, count=None, sort=None) -> dict:
        """
            Searches for data in a MongoDB collection. Results are paged (if 'count' and 'start_index' are set).
            :param fields: Fields to be selected. Any field to be selected is tagged with a '1'. Any field to be exclu-
                           ded is tagged with a '0'. '1's and '0's cannot be combined. Examples:
                                - db.<table>.find({'_id': 1, 'name': 1}) --> SELECT _id, name FROM <table>
                                - db.<table>.find({'_id': 0}) --> SELECT <all fields but '_id' field> FROM <table>
            :param conditions: Conditions that data must met to be selected.
            :param start_index: Skips N values. When making paged calls, this parameter must have the value of the
                                key 'next_start_index' of the response of the previous call. When the response does not
                                have such key, no more data are available.
            :param count: Sets a maximum amount of values returned per call (if None, then there is no limit).
            :param sort: If not specified, uses a $natural sort. Otherwise, 'sort' can be a single string (sorts by the
                         field with that name, ascending), or a list of tuples with the following format:
                         [(field_1, <1 or -1>), ..., (field_N,  <1 or -1>)]. Examples:
                                - db.<table>.find().sort('name') --> SELECT * FROM <table> ORDER BY 'name'
                                - db.<table>.find().sort([('name', 1), ('price', -1)]) --> SELECT * FROM <table>
                                                                                           ORDER BY 'name', 'price' DESC
            :return: A dict with two values:
                        - data: A list of values, or None if there were not values.
                        - next_start_index: The index of the first element of the next page. If no more data are
                                            available, this value won't appear.
            :rtype: dict
        """
        cursor = self.collection.find(conditions, fields).sort(sort if sort else '$natural'). \
            limit(count + 1 if count else 0).skip(start_index if start_index is not None else 0)
        data = [x for x in cursor]
        cursor.close()
        data = {'data': data if data else []}
        if len(data['data']) > count if count else False:
            # Discarding last element (necessary to determine if there are more elements, but not requested)
            data['data'] = data['data'][:-1]
            # Retrieving next page's first index, only if there are more data
            data['next_start_index'] = (start_index if start_index is not None else 0) + count
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

    def get_last_elements(self, amount=1, filter=None):
        """
            Finds the last element(s) which meet(s) a given condition(s).
            :param amount: Number of elements to be retrieved. If this parameter is set to '1', it will return a single
                           element; otherwise, a list of them.
            :param filter: Filters the search to the elements which meet the specified conditions.
            :return: A deserialized JSON document, or a list of them, depending on the value of the 'amount' parameter.
                     If the collection has no items, this operation will return 'None'.
        """
        count = self.collection.count(filter=filter)
        if count == 0:
            return None
        else:
            result = list(self.collection.find(filter=filter).skip(count - amount))
            return result[0] if amount == 1 else result
