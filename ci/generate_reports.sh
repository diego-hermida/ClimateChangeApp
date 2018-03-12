#! /bin/bash

# Generating combined coverage report.
SUCCESS_COVERAGE=0;
SUCCESS_REPORT=0;
message 5 "[ACTION] Fetching coverage reports from Docker images.";
message 5 "[ACTION] Fetching test results reports from Docker images.";
mkdir ./coverage
mkdir ./test_results
CONTAINER_ID=$(docker create diegohermida/data_gathering_subsystem_api:latest_CI);
if [ $? != 0 ]; then
    SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
    SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
    message 3 "[WARNING] API Docker container could not be created.";
else
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/coverage/api.coverage ./coverage/.coverage.api;
    if [ $? != 0 ]; then
        SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
        message 3 "[WARNING] API coverage report could not be fetched.";
    fi
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/test_results/api_tests.xml ./test_results/api_tests.xml;
    if [ $? != 0 ]; then
        SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
        message 3 "[WARNING] API test results report could not be fetched.";
    fi
    docker rm ${CONTAINER_ID}
fi
CONTAINER_ID=$(docker create diegohermida/data_gathering_subsystem:latest_CI);
if [ $? != 0 ]; then
    SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
    SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
    message 3 "[WARNING] Data Gathering Subsystem Docker container could not be created.";
else
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/coverage/dgs.coverage ./coverage/.coverage.dgs;
    if [ $? != 0 ]; then
        SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
        message 3 "[WARNING] Data Gathering Subsystem coverage report could not be fetched.";
    fi
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/test_results/dgs_tests.xml ./test_results/dgs_tests.xml;
    if [ $? != 0 ]; then
        SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
        message 3 "[WARNING] Data Gathering Subsystem test results report could not be fetched.";
    fi
    docker rm ${CONTAINER_ID}
fi
CONTAINER_ID=$(docker create diegohermida/data_conversion_subsystem:latest_CI);
if [ $? != 0 ]; then
    SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
    SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
    message 3 "[WARNING] Data Conversion Subsystem Docker container could not be created.";
else
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/coverage/dcs.coverage ./coverage/.coverage.dcs;
    if [ $? != 0 ]; then
        SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
        message 3 "[WARNING] Data Conversion Subsystem coverage report could not be fetched.";
    fi
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/test_results/dcs_tests.xml ./test_results/dcs_tests.xml;
    if [ $? != 0 ]; then
        SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
        message 3 "[WARNING] Data Conversion Subsystem test results report could not be fetched.";
    fi
    docker rm ${CONTAINER_ID}
fi
CONTAINER_ID=$(docker create diegohermida/telegram_bot:latest_CI);
if [ $? != 0 ]; then
    SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
    SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
    message 3 "[WARNING] Telegram Configurator Docker container could not be created.";
else
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/coverage/telegram.coverage ./coverage/.coverage.telegram;
    if [ $? != 0 ]; then
        SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
        message 3 "[WARNING] Telegram Configurator coverage report could not be fetched.";
    fi
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/test_results/telegram_tests.xml ./test_results/telegram_tests.xml;
    if [ $? != 0 ]; then
        SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
        message 3 "[WARNING] Telegram Configurator test results report could not be fetched.";
    fi
    docker rm ${CONTAINER_ID}
fi
CONTAINER_ID=$(docker create diegohermida/utilities:latest_CI);
if [ $? != 0 ]; then
    SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
    SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
    message 3 "[WARNING] Utilities Docker container could not be created.";
else
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/coverage/util.coverage ./coverage/.coverage.util;
    if [ $? != 0 ]; then
        SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
        message 3 "[WARNING] Utilities coverage report could not be fetched.";
    fi
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/test_results/util_tests.xml ./test_results/util_tests.xml;
    if [ $? != 0 ]; then
        SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
        message 3 "[WARNING] Utilities test results report could not be fetched.";
    fi
    docker rm ${CONTAINER_ID}
fi
if (( $SUCCESS_COVERAGE == 0 )); then
    exit_with_message 1 "[ERROR] No coverage reports have been fetched in order to generate a merged coverage report." 1;
fi
if (( $SUCCESS_REPORT == 0 )); then
    exit_with_message 1 "[ERROR] No test results reports have been fetched." 1;
fi
message 2 "[SUCCESS] XML test results reports successfully saved to \"./test_results/\"."
message 5 "[ACTION] Generating merged coverage report.";
docker-compose up -d coverage_CI
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] Coverage merge report Docker container could not be created." 1;
else
    CONTAINER_ID=$(docker create diegohermida/coverage:latest_CI);
    if [ $? != 0 ]; then
        exit_with_message 1 "[ERROR] Coverage merge report Docker container could not be created." 1;
    else
        docker cp ${CONTAINER_ID}:/ClimateChangeApp/code/coverage/coverage.xml ./coverage/coverage.xml;
        if [ $? != 0 ]; then
            SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
            exit_with_message 1 "[ERROR] Merged coverage report could not be fetched." 1;
        fi
        docker rm ${CONTAINER_ID}
    fi
fi
message 2 "[SUCCESS] XML coverage report successfully generated to \"./coverage/coverage.xml\"."
