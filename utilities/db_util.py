from global_config.config import GLOBAL_CONFIG
from os import environ
from pymongo import MongoClient


def drop_database(database=GLOBAL_CONFIG['MONGODB_DATABASE']):
    """
        Deletes all contents from a database.
        :param database: Database name. Defaults to GLOBAL_CONFIG.MONGODB_DATABASE
    """
    c = MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'), 
                    port=int(environ.get(GLOBAL_CONFIG['MONGODB_PORT'], 27017)),
                    authSource=GLOBAL_CONFIG['MONGODB_ADMIN'],
                    serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                    username=GLOBAL_CONFIG['MONGODB_ROOT'], password=GLOBAL_CONFIG['MONGODB_ROOT_PASSWORD'],
                    authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM'], maxPoolSize=1)
    try:
        c.drop_database(database)
    finally:
        c.close()


def create_user(username: str, password: str, roles: list, database=GLOBAL_CONFIG['MONGODB_DATABASE']):
    """
        Creates a MongoDB user, with the name, password and roles passed as arguments.
        :param username: User name.
        :param password: User password.
        :param roles: User roles.
        :param database: Database name. Defaults to GLOBAL_CONFIG.MONGODB_DATABASE
    """
    c = MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'), 
                    port=int(environ.get(GLOBAL_CONFIG['MONGODB_PORT'], 27017)),
                    authSource=GLOBAL_CONFIG['MONGODB_ADMIN'],
                    serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                    username=GLOBAL_CONFIG['MONGODB_ROOT'], password=GLOBAL_CONFIG['MONGODB_ROOT_PASSWORD'],
                    authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM'], maxPoolSize=1)
    try:
        c.get_database(database).command('createUser', username, pwd=password, roles=roles)
    except Exception:
        raise
    finally:
        c.close()


def drop_user(username=GLOBAL_CONFIG['MONGODB_USERNAME'], database=GLOBAL_CONFIG['MONGODB_DATABASE']) -> bool:
    """
        Drops an user.
        :param username: Name of the user to be removed.
        :param database: Database name. Defaults to GLOBAL_CONFIG.MONGODB_DATABASE
        :return: True, if the user has been successfully dropped; False, otherwise.
    """
    c = MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'), 
                    port=int(environ.get(GLOBAL_CONFIG['MONGODB_PORT'], 27017)),
                    authSource=GLOBAL_CONFIG['MONGODB_ADMIN'],
                    serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                    username=GLOBAL_CONFIG['MONGODB_ROOT'], password=GLOBAL_CONFIG['MONGODB_ROOT_PASSWORD'],
                    authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM'], maxPoolSize=1)
    try:
        return c.get_database(database).command('dropUser', username)
    finally:
        c.close()


def bulk_create_authorized_users(users: list, database=GLOBAL_CONFIG['MONGODB_DATABASE']) -> int:
    """
        Creates N authorized users, given a list of users.
        If an user was already authorized, this operation does NOT update its data --> avoiding DoS.
        :param users: List of users. Each user must be a JSON serializable object, with the following structure:
                                          {'_id': <username>, 'token': <token>}
        :param database: Database name. Defaults to GLOBAL_CONFIG.MONGODB_DATABASE
        :return: The number of successfully upserted users.
    """
    from pymongo import UpdateOne
    ops = []
    for user in users:
        # Changing "$set" to "$setOnInsert" FIXES [BUG-029].
        ops.append(UpdateOne({'_id': user['_id']}, update={'$setOnInsert': user}, upsert=True))
    c = MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'), 
                    port=int(environ.get(GLOBAL_CONFIG['MONGODB_PORT'], 27017)),
                    authSource=GLOBAL_CONFIG['MONGODB_ADMIN'],
                    serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                    username=GLOBAL_CONFIG['MONGODB_ROOT'], password=GLOBAL_CONFIG['MONGODB_ROOT_PASSWORD'],
                    authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM'], maxPoolSize=1)
    try:
        result = c.get_database(database).get_collection(GLOBAL_CONFIG['MONGODB_API_AUTHORIZED_USERS_COLLECTION']).\
                bulk_write(ops)
        return result.bulk_api_result['nInserted'] + result.bulk_api_result['nMatched'] + result.bulk_api_result[
            'nUpserted']
    finally:
        c.close()


def ping_database():
    """
        Performs a connection attempt, to ensure database is up. Regardless of the error, the client will be closed.
        :raises EnvironmentError: If any error occurs during the process.
    """
    c = MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'), 
                    port=int(environ.get(GLOBAL_CONFIG['MONGODB_PORT'], 27017)),
                    authSource=GLOBAL_CONFIG['MONGODB_ADMIN'],
                    serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                    username=GLOBAL_CONFIG['MONGODB_ROOT'], password=GLOBAL_CONFIG['MONGODB_ROOT_PASSWORD'],
                    authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM'], maxPoolSize=1)
    try:
        c.server_info()
    except Exception as exc:
        raise EnvironmentError from exc
    finally:
        c.close()


def get_and_increment_execution_id(subsystem_id: int, database=GLOBAL_CONFIG['MONGODB_DATABASE'], increment=True) -> int:
    """
        Retrieves the current execution ID. Each time this value is retrieved, it is auto-incremented in one unit.
        Postcondition: The execution ID is auto-incremented in one unit.
        :param subsystem_id: ID of the Data Gathering Subsystem.
        :param database: Database name. Defaults to GLOBAL_CONFIG.MONGODB_DATABASE
        :param increment: If True, the execution ID will be incremented (default).
        :return: An integer, containing the current execution ID.
    """
    c = MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'), 
                    port=int(environ.get(GLOBAL_CONFIG['MONGODB_PORT'], 27017)),
                    authSource=GLOBAL_CONFIG['MONGODB_ADMIN'],
                    serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                    username=GLOBAL_CONFIG['MONGODB_ROOT'], password=GLOBAL_CONFIG['MONGODB_ROOT_PASSWORD'],
                    authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM'], maxPoolSize=1)
    try:
        return c.get_database(database).get_collection(GLOBAL_CONFIG['MONGODB_STATS_COLLECTION']).find_one_and_update(
                {'_id': {'execution_id': True, 'subsystem_id': subsystem_id}},
                {'$inc': {'value': 1}}, fields={'value': 1}, new=True, upsert=True)['value'] if increment else \
                    c.get_database(database).get_collection(GLOBAL_CONFIG['MONGODB_STATS_COLLECTION']).find_one({'_id':
                    {'execution_id': True, 'subsystem_id': subsystem_id}})['value']
    finally:
        c.close()


def get_connection_pool(username=GLOBAL_CONFIG['MONGODB_USERNAME'], password=GLOBAL_CONFIG['MONGODB_USER_PASSWORD'],
                        database=GLOBAL_CONFIG['MONGODB_DATABASE']) -> MongoClient:
    """
        Initialises a new connection pool with the GLOBAL_CONFIG parameters as defaults.
        However, username and password can be changed.
        :param username: User name.
        :param password: User's password.
        :param database: Database name. Defaults to GLOBAL_CONFIG.MONGODB_DATABASE
        :return: A pymongo.MongoClient instance.
    """
    return MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'), 
                       port=int(environ.get(GLOBAL_CONFIG['MONGODB_PORT'], 27017)),
                       authSource=database, serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                       username=username, password=password, authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM'],
                       maxPoolSize=GLOBAL_CONFIG['MONGODB_MAX_POOL_SIZE'],
                       waitQueueMultiple=GLOBAL_CONFIG['MONGODB_WAIT_QUEUE_MULTIPLE'],
                       waitQueueTimeoutMS=GLOBAL_CONFIG['WAIT_QUEUE_MILLISECONDS_TIMEOUT'])


class MongoDBCollection:
    """
        This class acts as an abstraction to a MongoDB Collection. It provides a wrapper interface for some operations,
        such as initialization and closure of connections, search operations...
        It also provides transparent access to connection pools. When creating MongoDBCollection instances, if the
        parameter "use_pool" is set (by default), the first instance will create the connection pool and the following
        ones will reuse the same one.
        Connection pools are saved in a dictionary, whose keys are the hash of the tuple (username, database); where
        "username" and "database" are passed to the constructor.
        This class is thread-safe, since a "threading.Lock" object is used to synchronize the creation and access to
        the connection pools.
    """
    import threading

    _pools = {}
    _lock = threading.Lock()

    def __init__(self, collection_name, use_pool=True, username=GLOBAL_CONFIG['MONGODB_USERNAME'],
                 password=GLOBAL_CONFIG['MONGODB_USER_PASSWORD'], database=GLOBAL_CONFIG['MONGODB_DATABASE']):
        """
            Initializes a collection to perform database operations. The actual PyMongo collection is the only exposed
            attribute, in order to perform all its operations.
            Instantiation will fail if the database is down, since the connection is validated at this point.
            Postcondition: A valid connection with the collection has been established.
            :param collection_name: Name of the collection to be connected to.
            :param use_pool: Uses a connection pool instead of creating a single connection. The connection pool will
                             be initialized the first time a MongoDBCollection object is created.
                             The MongoDBCollection will store a connection pool per (username, database).
            :param username: User name. Defaults to GLOBAL_CONFIG.MONGODB_USERNAME
            :param password: User's password. Defaults to GLOBAL_CONFIG.MONGODB_USER_PASSWORD
            :param database: Database name. Defaults to GLOBAL_CONFIG.MONGODB_DATABASE
        """
        self._collection_name = collection_name
        self._database_name = database
        self._username = username
        self._use_pool = use_pool
        if use_pool:
            _id = hash((username, database))
            try:
                self._client = MongoDBCollection._pools[_id]
            except KeyError:
                MongoDBCollection._lock.acquire()
                if not MongoDBCollection._pools.get(_id):
                    MongoDBCollection._pools[_id] = get_connection_pool(username=username, password=password,
                                                                        database=database)
                MongoDBCollection._lock.release()
                self._client = MongoDBCollection._pools[_id]
        else:
            self._client = MongoClient(host=environ.get(GLOBAL_CONFIG['MONGODB_SERVER'], 'localhost'),
                    port=int(environ.get(GLOBAL_CONFIG['MONGODB_PORT'], 27017)), authSource=database,
                    serverSelectionTimeoutMS=GLOBAL_CONFIG['MONGODB_DB_MAX_MILLISECONDS_WAIT'],
                    username=username, password=password, authMechanism=GLOBAL_CONFIG['MONGODB_AUTH_MECHANISM'])
        self._client.server_info()  # Checks valid connection.
        self.collection = self._client.get_database(database).get_collection(collection_name)

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
        self.collection = self._client.get_database(self._database_name).get_collection(
                collection_name if collection_name else self._collection_name)

    def find(self, fields=None, conditions=None, start_index=None, count=None, sort=None) -> (list, int):
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
            :return: A tuple with two values:
                        - data: A list of values, or None if there were not values.
                        - next_start_index: The index of the first element of the next page. If no more data are
                                            available, this value will be None.
            :rtype: tuple
        """
        cursor = self.collection.find(conditions, fields).sort(sort if sort else '$natural').limit(
                count + 1 if count else 0).skip(start_index if start_index is not None else 0)
        data = [x for x in cursor]
        cursor.close()
        data = data if data else []
        next_start_index = None
        if len(data) > count if count else False:
            # Discarding last element (necessary to determine if there are more elements, but not requested)
            data = data[:-1]
            # Retrieving next page's first index, only if there are more data
            next_start_index = (start_index if start_index is not None else 0) + count
        return data, next_start_index

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

    def __str__(self):
        return 'MongoDBCollection [collection=%s, database=%s, username=%s, pool=%s' % (self._collection_name,
                self._database_name, self._username, self._use_pool)
