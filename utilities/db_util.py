import pymongo

from utilities.util import get_config


def connect(collection_name=None):
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


def find(collection, last_id=None, count=None):
    """
        Searches for data in a MongoDB collection. "_id" field is used to perform comparison between objects.
        :param collection: A valid connection to a MongoDB connection.
        :param last_id: Data will be retrieved from the next value of 'last_id' (or from the beginning if last_id is None)
        :param count: Sets a maximum amount of values returned per function call (no limit if count is None).
        :return: A list containing matching objects, or None if no data was found.
        :rtype: list
    """
    if last_id is None:
        cursor = collection.find().sort('_id').limit(0 if count is None else count)  # 0 limit means "no limit"
    else:
        cursor = collection.find({'_id': {'$gt': last_id}}).sort('_id').limit(
            0 if count is None else count)  # gt: greater than
    data = [x for x in cursor]
    return None if not data else data
