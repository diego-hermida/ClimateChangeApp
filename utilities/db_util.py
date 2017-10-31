import pymongo

from utilities.util import get_config


def connect(collection_name=None):
    """
    Connects to a database and, if 'collection_name' isn't None, to a collection. Connection parameters are read from
    a configuration file (db_util.config)
    :param collection_name: Name of the collection to be connected to.
    :return: A valid connection to a collection, or to a database (if 'collection_name' is None)
    """
    config = get_config(__file__)
    client = pymongo.MongoClient(
        host=config['DB_SERVER'],
        port=config['DB_PORT'],
        authSource=config['DB_DATABASE'],
        serverSelectionTimeoutMS=config['DB_MAX_MILLISECONDS_WAIT'],
        username=config['DB_USERNAME'],
        password=config['DB_PASSWORD'],
        authMechanism=config['DB_AUTH_MECHANISM'])
    try:
        # Checks valid connection.
        client.server_info()
        # Returns Collection if collection_name is provided, otherwise returns Database
        database = client.get_database(config['DB_DATABASE'])
        return database if collection_name is None else database.get_collection(collection_name)
    except pymongo.errors.ServerSelectionTimeoutError as ex:
        raise ex
    except pymongo.errors.OperationFailure as ex:
        raise ex


def find(collection: str, fields=None, conditions=None, last_id=None, count=None, sort=None) -> dict:
    """
        Searches for data in a MongoDB collection. "_id" field is used to perform comparison between objects.
        :param collection: The collection name.
        :param last_id: Data will be retrieved from 'last_id' next value (or from the beginning if last_id is None)
        :param count: Sets a maximum amount of values returned per function call (no limit if count is None).
        :param fields: Fields to be selected. Any field to be selected is tagged with a '1'. Any field to be excluded is
                       tagged with a '0'. '1's and '0's cannot be combined. Examples:
                            - db.<table>.find({'_id': 1, 'name': 1, 'price':1}) --> SELECT id, name, price FROM <table>
                            - db.<table>.find({'_id': 0}) --> SELECT <all fields but '_id' field> FROM <table>
        :param conditions: Conditions that data must met to be selected. If "conditions" is None, a default condition
                           is imposed if 'last_id' isn't None: '_id' field must be greater than 'last_id'.
        :param sort: If not specified, uses a $natural sort. Otherwise, 'sort' can be a single string (ascending order
                     by that field), or a list of tuples with the following format:
                     [(field_1, <1 or -1>), ..., (field_N,  <1 or -1>)]. Examples:
                            - db.<table>.find().sort('name') --> SELECT * FROM <table> ORDER BY 'name'
                            - db.<table>.find().sort([('name', 1), ('price', -1)]) --> SELECT * FROM <table>
                                                                                       ORDER BY 'name', 'price' DESC
        :return: A dict with two values:
                    - data: A list of values, or None if there were not values.
                    - more: A boolean value, indicating whether retrieved data is the last or not.
        :rtype: dict
    """
    collection = connect(collection)
    if last_id:
        if not conditions:
            conditions = {}
        conditions['_id'] = {'$gt': last_id}
    cursor = collection.find(conditions, fields).sort(sort if sort else '$natural').limit(count + 1 if count else 0)
    data = [x for x in cursor]
    data = {'data': data if data else None, 'more': len(data) > count if count else False}
    if data['more']:
        # Discarding last element (necessary to determine if there are more elements, but not requested)
        data['data'] = data['data'][:-1]
    return data
