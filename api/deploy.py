import argparse
import sys
import yaml

from api.config.config import API_CONFIG
from data_gathering_subsystem.config.config import DGS_CONFIG
from global_config.global_config import GLOBAL_CONFIG
from os import environ
from pymongo import InsertOne
from pymongo.errors import DuplicateKeyError
from unittest import TestLoader, TextTestRunner
from utilities.db_util import MongoDBCollection, bulk_create_authorized_users, ping_database, create_user, \
    get_and_increment_execution_id
from utilities.import_dir import get_module_names
from utilities.log_util import get_logger
from utilities.util import remove_all_under_directory


def deploy(log_to_file=True, log_to_stdout=True, log_to_telegram=None):

    # Getting a logger instance
    logger = get_logger(__file__, 'DeployAPILogger', to_file=log_to_file, to_stdout=log_to_stdout, is_subsystem=False,
                        component=API_CONFIG['COMPONENT'], to_telegram=log_to_telegram)
    try:
        # Parsing command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--all', help='executes all deploy actions. This is the default option. If chosen, all '
                'other options will be ignored. Tests are not executed by default.', required=False, action='store_true')
        parser.add_argument('--db-user', help='creates the API MongoDB user', required=False,
                action='store_true')
        parser.add_argument('--add-users', help='adds the authorized users contained in the "authorized_users.config" '
                'file', required=False, action='store_true')
        parser.add_argument('--remove-files', help='removes all API .log files',
                required=False, action='store_true')
        parser.add_argument('--adapt-legacy-data', help='inserts a field in every document in MongoDB. This operation '
                                                        'should be run only once, and only when there is data collected'
                                                        ' by a Data Gathering Subsystem instance with version < v2.0.',
                            required=False, action='store_true')
        parser.add_argument('--with-tests', help='executes all the Subsystem tests', required=False,
                            action='store_true')
        parser.add_argument('--skip-all', help='does not execute any deploy step', required=False,
                            action='store_true')

        # Deploy args can be added from the "install.sh" script using environment variables.
        env_args = environ.get('DEPLOY_ARGS', None)
        if env_args:
            for arg in env_args.split(' '):
                sys.argv.append(arg)
        args = parser.parse_args()

        # If --skip-all, then the operations will be omitted.
        if args.skip_all:
            logger.info('Deploy operations have been skipped.')
            exit(0)
        if args.all and any([args.db_user, args.add_users, args.remove_files]):
            logger.info('Since "--all" option has been passed, any other option is excluded.')
        elif not any([args.all, args.db_user, args.add_users, args.remove_files]) and not sys.argv[1:]:
            logger.info('Since no option has been passed, using "--all" as the default option.')
            args = argparse.Namespace(all=True, with_tests=False)

        # 1. [Default] Verifying MongoDB is up (required both for adding users and tests).
        try:
            ping_database()
            logger.info('MongoDB daemon is up and reachable.')
        except EnvironmentError:
            logger.error('MongoDB service is down. Deploy will be aborted, since an active MongoDB service is required '
                    'for this operations.')
            exit(1)

        # 2. Creating MongoDB user.
        if args.all or args.db_user:
            logger.info('Creating Data Gathering Subsystem API user.')
            try:
                create_user(username=GLOBAL_CONFIG['MONGODB_API_USERNAME'],
                            password=GLOBAL_CONFIG['MONGODB_API_USER_PASSWORD'],
                            roles=[{"role": "read", "db": GLOBAL_CONFIG['MONGODB_DATABASE']}])
                logger.info('Successfully created API user.')
            except DuplicateKeyError:
                logger.warning('User was not created because it did already exist in database.')

        # 3. Adding API authorized users.
        if args.all or args.add_users:
            logger.info('Adding API authorized users to database.')
            with open(API_CONFIG['AUTHORIZED_USERS_FILEPATH'], 'r', encoding='utf-8') as f:
                users = yaml.load(f)
            authorized_users = []
            for user in users['authorized_users']:
                user_data = users['authorized_users'][user]
                if user_data.get('token') is None or user_data.get('scope') is None:
                    logger.error('Authorized user "%s" does not have the required fields. This may lead to unexpected '
                                 'errors while using API. Deploy will be aborted.' % user)
                    exit(1)
                authorized_users.append({'_id': user, 'token': user_data['token'], 'scope': user_data['scope']})
            added_users = bulk_create_authorized_users(authorized_users)
            if len(authorized_users) == added_users:
                logger.info('All API authorized users have been added (%d).' % added_users)
            else:
                logger.error('Some API authorized users have not been added (%d out of %d). Deploy will be aborted. '%(
                        added_users, len(authorized_users)))
                exit(1)

        # 4. Executing all tests
        if args.with_tests:
            logger.info('Running all the API tests.')
            loader = TestLoader()
            suite = loader.discover(API_CONFIG['ROOT_API_FOLDER'])
            runner = TextTestRunner(failfast=True, verbosity=2)
            results = runner.run(suite)
            sys.stderr.flush()
            logger = get_logger(__file__, 'DeployAPILogger', to_file=log_to_file, to_stdout=log_to_stdout,
                    is_subsystem=False, component=API_CONFIG['COMPONENT'], to_telegram=log_to_telegram)
            if results.wasSuccessful():
                logger.info('All tests passed.')
            else:
                logger.error('Some tests did not pass. Further info is available in the command line output.')
                exit(1)

        # 5. Emptying Subsystem's logs and '.state' files.
        if args.all or args.remove_files:
            logger.info('Removing log base directory: %s' % (API_CONFIG['API_LOG_FILES_ROOT_FOLDER']))
            try:
                remove_all_under_directory(API_CONFIG['API_LOG_FILES_ROOT_FOLDER'])
            except FileNotFoundError:
                logger.info('Log base directory does not exist, so it cannot be removed.')

        if args.adapt_legacy_data:
            logger.info('Adapting legacy data by inserting an "execution_id" field in all collected documents.')
            module_names = get_module_names(DGS_CONFIG['DATA_MODULES_PATH'], recursive=True,
                                             base_package=DGS_CONFIG['DATA_COLLECTOR_BASE_PACKAGE'], only_names=True)
            if not module_names:
                logger.info('The Data Gathering Subsystem instance of this ClimateChangeApp instance does not have any'
                            ' DataCollector module. This operation will stop now.')
                exit(0)
            else:
                try:
                    logger.info('Retrieving last execution ID from database.')
                    execution_id = get_and_increment_execution_id(DGS_CONFIG['SUBSYSTEM_INSTANCE_ID'], increment=False)
                except TypeError:
                    execution_id = 1
                    logger.warning('Execution ID could not be retrieved. Setting default execution ID to "1".')
                logger.info('Adapted data will have the execution ID: %d' % execution_id)
                ok = []
                zero = []
                missing = []
                total = 0
                updated = 0
                for module in module_names:
                    c = MongoDBCollection(collection_name=module, use_pool=True)
                    count = c.collection.count()
                    if count == 0:
                        zero.append(module)
                        continue
                    total += count
                    res = c.collection.update_many({}, {'$set': {DGS_CONFIG['EXECUTION_ID_DOCUMENT_FIELD']:
                            execution_id}}, upsert=False)
                    updated += res.modified_count
                    if res.matched_count == res.modified_count and res.modified_count == count:
                        ok.append(module)
                    else:
                        missing.append(module)
                logger.info('Operation results:\n\t- Collections with 0 elements: %s\n\t- Collections with all '
                            'documents updated: %s\n\t- Collections with missing updated data: %s\n\t- Total elements: '
                            '%d\n\t- Updated elements: %d\n\t- Success: %s' % (zero, ok, missing, total, updated,
                                                                               total == updated))
                if missing:
                    logger.warning('Some data could not be updated. Thus, the Data Gathering Subsystem API will not '
                            'serve those data, since no "%s" field is present.' % DGS_CONFIG['EXECUTION_ID_DOCUMENT_FIELD'])
                    exit(1)
            # Adapting data per modules
            INVALID_TYPES = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
            successful_modules = []
            unsuccessful_modules = []
            total_inserted = 0
            total_removed = 0
            for module in module_names:
                logger.info('Adapting data for collection: %s' % module)
                if module in ['countries', 'locations']:
                    successful_modules.append(module)
                    logger.info('Further data adaptions aren\'t necessary for this module.')
                    continue
                c = MongoDBCollection(collection_name=module, use_pool=True)
                if module != 'historical_weather':
                    data = c.find(conditions={'_id': {'$type': INVALID_TYPES}})['data']
                    data_size = len(data)
                if not data_size:
                    successful_modules.append(module)
                    logger.info('Further data adaptions aren\'t necessary for this module.')
                    continue
                to_insert = []
                if module == 'air_pollution':
                    for v in data:
                        v['station_id'] = v['_id']['station_id']
                        v['time_utc'] = v['_id']['time_utc']
                        del v['_id']
                        to_insert.append(InsertOne(v))
                elif module == 'country_indicators':
                    for v in data:
                        v['indicator'] = v['_id']['indicator']
                        v['country_id'] = v['_id']['country']
                        v['year'] = v['_id']['year']
                        del v['_id']
                        to_insert.append(InsertOne(v))
                elif module == 'current_conditions':
                    for v in data:
                        v['station_id'] = v['_id']['station_id']
                        v['time_utc'] = v['_id']['time']
                        del v['_id']
                        to_insert.append(InsertOne(v))
                elif module == 'energy_sources':
                    for v in data:
                        v['country_id'] = v['_id']['country_id']
                        v['time_utc'] = v['_id']['time_utc']
                        del v['_id']
                        to_insert.append(InsertOne(v))
                elif module == 'future_emissions':
                    for v in data:
                        del v['_id']
                        to_insert.append(InsertOne(v))
                elif module == 'historical_weather':
                    logger.warning('Data adaption for this module may take several minutes.')
                    # Groups of 2000 elements: 3m 40s and 2.15 GB peak.
                    # Groups of 1000 elements: 3m 58s and 1.34 GB peak.
                    logger.info('Adapting data in groups of 2000 elements, avoiding swapping into disk. Memory usage '
                            'should be bounded between 800 MB and 2.2 GB.')
                    _inserted = 0
                    start_index = 0
                    data_size = c.collection.count({'_id': {'$type': INVALID_TYPES}})
                    while True:
                        data = c.find(conditions={'_id': {'$type': INVALID_TYPES}}, start_index=start_index,
                                count=2000)
                        for v in data['data']:
                            v['date_utc'] = v['_id']['date_utc']
                            del v['_id']
                            to_insert.append(InsertOne(v))
                        _inserted += c.collection.bulk_write(to_insert).inserted_count
                        logger.debug('Inserted: %d elements (out of %d).' % (_inserted, data_size))
                        to_insert = []
                        start_index = data.get('next_start_index')
                        if start_index is None:
                            inserted = _inserted
                            break
                elif module == 'ocean_mass':
                    for v in data:
                        v['type'] = v['_id']['type']
                        v['time_utc'] = v['_id']['utc_date']
                        del v['_id']
                        to_insert.append(InsertOne(v))
                elif module == 'sea_level_rise':
                    for v in data:
                        v['time_utc'] = v['_id']
                        del v['_id']
                        to_insert.append(InsertOne(v))
                elif module == 'weather_forecast':
                    for v in data:
                        v['station_id'] = v['_id']['station_id']
                        del v['_id']
                        to_insert.append(InsertOne(v))
                if module != 'historical_weather':
                    inserted = c.collection.bulk_write(to_insert).inserted_count
                removed = c.collection.remove({'_id': {'$type': INVALID_TYPES}})['n']
                success = inserted == removed
                total_inserted += inserted
                total_removed += removed
                if success:
                    successful_modules.append(module)
                else:
                    unsuccessful_modules.append(module)
                logger.info('Result for collection "%s":\n\t- Total elements: %d\n\t- Inserted: %d\n\t- '
                        'Removed: %d\n\t- Success: %s' % (module, data_size, inserted, removed, success))
            logger.info('Summary:\n\t- Successful modules: %s\n\t- Unsuccessful modules: %s\n\t- Total inserted: %d'
                    '\n\t- Total removed: %d\n\t- Success: %s' % (successful_modules, unsuccessful_modules,
                        total_inserted, total_removed, total_inserted == total_removed))

    except Exception:
        logger.exception('An error occurred while performing deploy operations.')
        exit(1)  # Any raised exception will cause an anomalous exit.


if __name__ == '__main__':
    deploy(log_to_file=False, log_to_stdout=True)
