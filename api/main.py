from api.settings import API_ALIVE_CACHE_TIME
from eve import Eve
from eve.auth import TokenAuth
from global_config.global_config import GLOBAL_CONFIG
from flask import json, request
from functools import wraps
from os import environ
from utilities.db_util import MongoDBCollection, ping_database
from utilities.log_util import get_logger
from utilities.util import current_date_in_millis


class ValidationError(ValueError):
    def __init__(self, message):
        self.message = message


class _AppTokenAuth(TokenAuth):
    """
        HTTP requests must contain an 'Authorization' header.
    """
    def check_auth(self, token, allowed_roles, resource, method):
        global _scope
        user = app.data.driver.db[GLOBAL_CONFIG['MONGODB_API_AUTHORIZED_USERS_COLLECTION']].find_one(
                {'token': token})
        if user:
            try:
                _scope = user['scope']
            except KeyError:
                _scope = None
        return user is not None


app = Eve(auth=_AppTokenAuth)
_api_alive = True
_api_alive_last_update = None
_scope = None


def require_auth(f):
    """
        By decorating an API endpoint with this, all API calls are required to provide an "Authorization: Bearer {TOKEN}"
        header inside the HTTP request.
        IMPORTANT: Each call verifies API is up (using cache for close calls), and a 503 Service Unavailable response
        will be sent if the database is down.
        :param f: Function to be wrapped.
        :return: Everything that the wrapped function returns.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        _alive()
        if _api_alive:
            if app.auth.authorized(None, None, None):
                return f(*args, **kwargs)
            else:
                return app.response_class(response=_dumps({"_status": "ERR", "_error": {"code": 401, "message":
                        "Please provide proper credentials"}}), status=401, mimetype='application/json')
        else:
            return app.response_class(response=_dumps(
                    {"_status": "ERR", "_error": {"code": 503, "message": "API is unavailable."}}),
                                      status=503, mimetype='application/json')
    return wrapped


def require_validation(f):
    """
        By decorating an API endpoint with this, all API calls are surrounded with try-except clauses, which intercept
        ValidationError(s).
        :param f: Function to be wrapped.
        :return: Everything that the wrapped function returns, or the error message contained in the exception.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as error:
            return error.message
    return wrapped


def require_scope(f):
    """
        By decorating an API endpoint with this, all API calls are required of a token scope. If no scope is provided,
        a 400 Bad Request response will be automatically sent.
        :param f: Function to be wrapped.
        :return: Everything that the wrapped function returns, or a 400 Bad Request response.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        global _scope
        try:
            if _scope:
                result = f(*args, **kwargs)
                _scope = None
                return result
            else:
                return app.response_class(response=_dumps({"_status": "ERR", "_error": {"code": 400, "message":
                    "A token scope is required and your token does not have one. If this is not your fault, contact "
                    "the API developer."}}), status=400, mimetype='application/json')
        except ValidationError as error:
            return error.message
    return wrapped


def validate_integer(param_name, only_positive=False, required=False) -> int:
    """
        Validates an integer from the parameters contained in the HTTP request.
        :param param_name: Name of the parameter to be validated.
        :param only_positive: If True, validation will only succeed if the parameter is a positive integer.
        :param required: If True, validation will only succeed if the parameter is present.
        :return: The integer, parsed and validated.
        :raises ValidationError: If validation fails.
    """
    param = request.args.get(param_name, default=None)
    error_msg = None
    try:
        param = int(param) if param else None
        if param is None and required:
            error_msg = "Parameter '%s' is mandatory." % param_name
        if only_positive and param is not None and param <= 0:
            error_msg = "Parameter '%s' must be a positive integer." % param_name
    except:
        error_msg = "Parameter '%s' must be an integer." % param_name
    if error_msg:
        raise ValidationError(app.response_class(response=_dumps({"_status": "ERR", "_error": {"code": 400,
                "message": error_msg}}), status=400,
                mimetype='application/json'))
    return param


def _set_module_names():
    """
        Internal function that queries MongoDB in order to retrieve all valid module names.
    """
    collection = MongoDBCollection(GLOBAL_CONFIG['MONGODB_STATS_COLLECTION'])
    result = collection.collection.find_one({'_id': {'subsystem_id': _scope, 'type': 'aggregated'}})
    collection.close()
    return list(result['per_module'].keys()) if result else []


def _alive():
    """
        Internal function that queries MongoDB to determine if database is up. It has a cache-mechanism.
    """
    global _api_alive
    global _api_alive_last_update
    time = current_date_in_millis()
    if _api_alive is None or _api_alive_last_update is None or _api_alive_last_update + API_ALIVE_CACHE_TIME < time:
        try:
            ping_database()
            _api_alive = True
        except EnvironmentError:
            _api_alive = False
        finally:
            _api_alive_last_update = time


def _dumps(obj) -> str:
    """
        Does the same as the json.dumps function, but adds a newline character after the serialization.
        :param obj: Object to be serialized
        :return: The serialized object, plus a newline character.
    """
    return json.dumps(obj) + '\n'


@app.route('/modules')
@require_auth
@require_scope
def modules():
    """
        API endpoint. Retrieves all module name(s), i.e. all DataCollector(s).
        Features: Cache. Module names are only read from database at least, every 5 minutes.
        HTTP Method: GET
        Requires authorization: Yes
        Response code: HTTP 200 OK
        Content type: application/json
        Content example: {"modules": [module1, module2, module3], "updated": 1518032300957}
        Errors: 401 Unauthorized, if the user did not provide the "Authentication" header with a valid token inside the
                HTTP request.
    """
    result = {'modules': _set_module_names(), 'updated': current_date_in_millis()}
    return app.response_class(response=_dumps(result), status=200, mimetype='application/json')


@app.route('/executionStats')
@require_auth
@require_scope
@require_validation
def execution_stats():
    """
        API endpoint. Retrieves statistics from an execution. This endpoint accepts the
        following parameters:
            - executionId: If this parameter is present, retrieves statistics from the execution with such ID.
                           Otherwise, retrieves statistics from the last execution.
        HTTP Method: GET
        Requires authorization: Yes
        Response code: HTTP 200 OK
        Content type: application/json
        Content example: {"execution_id": 96742, "updated": 1518032300957}
        Errors:
            - 400 Bad Request, if parameters are invalid (bad types/values).
            - 401 Unauthorized, if the user did not provide the "Authentication" header with a valid token inside the
              HTTP request.
            - 404 Not Found, if the Data Gathering Subsystem has not yet been executed and, therefore, the execution ID
              has not been set; or there are no data for such execution ID.
    """
    execution_id = validate_integer('executionId', only_positive=True, required=False)
    collection = MongoDBCollection(GLOBAL_CONFIG['MONGODB_STATS_COLLECTION'])
    if execution_id is None:
        try:
            execution_id = collection.collection.find_one({'_id': {'subsystem_id': _scope, 'type': 'aggregated'}})[
                'last_execution_id']
        except TypeError:
            return app.response_class(response=_dumps({'stats': None, 'reason': 'The Data Gathering Subsystem '
                    'has not yet been executed.', 'last_execution_id': None}), status=404, mimetype='application/json')
    result = collection.collection.find_one(filter={'_id': {'subsystem_id': _scope, 'execution_id': execution_id,
            'type': 'last_execution'}})
    if result:
        return app.response_class(response=_dumps(result), status=200, mimetype='application/json')
    else:
        try:
            execution_id = collection.collection.find_one({'_id': {'subsystem_id': _scope, 'type': 'aggregated'}})[
                'last_execution_id']
        except TypeError:
            return app.response_class(response=_dumps({'stats': None, 'reason': 'The Data Gathering Subsystem '
                    'has not yet been executed.'}), status=404, mimetype='application/json')
        return app.response_class(response=_dumps({'stats': None, 'reason': 'Unable to find stats for the given'
            ' execution ID.', 'last_execution_id': execution_id}), status=404, mimetype='application/json')


@app.route('/data/<module_name>')
@require_auth
@require_scope
@require_validation
def data(module_name: str):
    """
        API endpoint. Retrieves collected data from a module. This endpoint accepts the following parameters:
            - startIndex: Optional. Should be 0 (or omitted) on the first call, and the value of 'next_start_index' on
                          the following ones.
            - limit: Optional. The number of elements to be retrieved.
            - executionId: If present, the call only returns data collected in the execution with such ID.
        WARNING: If no parameters are set, the operation will retrieve all module data. This can lead to huge amounts
        of data being transferred, which might overload the network.
        HTTP Method: GET
        Requires authorization: Yes
        Response code: HTTP 200 OK
        Content type: application/json
        Content example: {"data": [<data>], "more": true|false}
        Errors:
            - 400 Bad Request, if parameters are invalid (bad types/values).
            - 401 Unauthorized, if the user did not provide the "Authentication" header with a valid token inside the
              HTTP request.
            - 404 Not Found, if the module name does not refer to an existing module.
    """
    start_index = validate_integer('startIndex', only_positive=True)
    count = validate_integer('limit', only_positive=True)
    execution_id = validate_integer('executionId', only_positive=True)
    _set_module_names()
    if module_name not in _set_module_names():
        return app.response_class(response=_dumps(
                {"_status": "ERR", "_error": {"code": 404, "message": "Such module does not exist. Make a call to the "
                "'/modules' endpoint in order to retrieve valid modules."}}), status=404, mimetype='application/json')
    collection = MongoDBCollection(module_name)
    result = collection.find(conditions={'_execution_id': execution_id} if execution_id else {}, sort='_id',
            start_index=start_index, count=count)
    return app.response_class(response=_dumps(result), status=200, mimetype='application/json')


@app.route('/alive')
def alive():
    """
        API endpoint. Retrieves if either the MongoDB database and the API are up.
        HTTP Method: GET
        Requires authorization: No
        Response code: HTTP 200 OK
        Content type: application/json
        Content format: {'alive': true|false, 'updated': 1518032300957}
        Errors: 503 Service Unavailable, if the database is down.
    """
    _alive()
    return app.response_class(response=_dumps({'alive': _api_alive, 'updated': _api_alive_last_update}),
                              status=200 if _api_alive else 503, mimetype='application/json')


def main(log_to_stdout=True, log_to_file=True):
    # Getting logger instance
    logger = get_logger(__file__, name='APILogger', to_file=log_to_file, to_stdout=log_to_stdout, is_subsystem=False)

    # This provisional solution FIXES [BUG-015]
    if environ.get('LOCALHOST_IP') is None:
        logger.critical('LOCALHOST_IP must exist as an ENVIRONMENT VARIABLE at execution time. Aborting Subsystem.')
        exit(1)
    else:
        logger.debug('Environment variable LOCALHOST_IP found, with value: "%s". To override it, use --env '
                     'LOCALHOST_IP=<IP> when invoking "docker run".' % (environ.get('LOCALHOST_IP')))
    # Launching API
    app.run(host='0.0.0.0')


if __name__ == '__main__':
    main(log_to_file=True, log_to_stdout=True)