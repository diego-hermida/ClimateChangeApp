import pymongo

from util.util import get_config


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
