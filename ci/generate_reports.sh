#! /bin/bash

# ---------- Functions ---------- #

source "./utilities/bash_util.sh";

# Displays script usage and exits.
# :param $1: Exit code.
function usage () {
    exit_with_message 1 "Fetches test results and coverage reports from Docker CI images, and generates a merged coverage
            \nreport. Reports will be saved to \"./test_results\" and \"./coverage\", respectively. Directories will be
            \ncreated if they doesn't exist.
            \n\n> usage: generate_reports.sh [-h] [--help] [--version] [--path-to-replace <path>]
            \n • -h, --help: shows this message.
            \n • --version: displays app's version.
            \n • --path-to-replace <path>: Replaces \"/ClimateChange/code\" with another path, so that coverage
            \n\t   report points to the real workspace path. Defaults to \"/ClimateChange/code\" (no-op)." $1;
}


# ---------- Definitions ---------- #

PATH_TO_REPLACE="/ClimateChangeApp/code";


# ---------- Argument manipulation ---------- #

# Parsing arguments
EXPECTED_INPUT=":h-:"
while getopts "$EXPECTED_INPUT" ARG; do
    case "${ARG}" in
        h) usage 0 ;;
        -) case ${OPTARG} in
                help) usage 0 ;;
                version) show_app_version ;;
                path-to-replace)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--path-to-replace" ${VAL};
                    PATH_TO_REPLACE=${VAL};
                ;;
                :) exit_with_message 1 "Illegal option: \"--$OPTARG\" requires an argument" >&2 ;;
                *) exit_with_message 1 "Unrecognized option: --$OPTARG" >&2 ;;
            esac
        ;;
        :) exit_with_message 1 "Illegal option: \"-$OPTARG\" requires an argument" >&2 ;;
        *) exit_with_message 1 "Unrecognized option: -$OPTARG" >&2 ;;
    esac
done


# Overriding default path?
if [ "$PATH_TO_REPLACE" == "/ClimateChangeApp/code" ]; then
    message -1 "[INFO] Keeping default file paths in the coverage report.";
else
    message -1 "[INFO] Replacing \"/ClimateChangeApp/code\" with a custom path: \"$PATH_TO_REPLACE\".";
fi


# ---------- Actions ---------- #

# Setting a decrementing counter. If one of these equals 0, report generation will be aborted.
SUCCESS_COVERAGE=5;
SUCCESS_REPORT=5;
message 5 "[ACTION] Fetching coverage reports from Docker images.";
message 5 "[ACTION] Fetching test results reports from Docker images.";

# Creating directories for saving reports.
mkdir ./coverage
mkdir ./test_results

# Saving reports to directories.
CONTAINER_ID=$(docker create diegohermida/api:latest_ci);
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
CONTAINER_ID=$(docker create diegohermida/data_gathering_subsystem:latest_ci);
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
CONTAINER_ID=$(docker create diegohermida/data_conversion_subsystem:latest_ci);
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
CONTAINER_ID=$(docker create diegohermida/web_application_subsystem:latest_ci);
if [ $? != 0 ]; then
    SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
    SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
    message 3 "[WARNING] Web Application Subsystem Docker container could not be created.";
else
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/coverage/web.coverage ./coverage/.coverage.web;
    if [ $? != 0 ]; then
        SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
        message 3 "[WARNING] Web Application Subsystem coverage report could not be fetched.";
    fi
    docker cp ${CONTAINER_ID}:/ClimateChangeApp/test_results/web_tests.xml ./test_results/web_tests.xml;
    if [ $? != 0 ]; then
        SUCCESS_REPORT=$((SUCCESS_REPORT - 1));
        message 3 "[WARNING] Web Application Subsystem test results report could not be fetched.";
    fi
    docker rm ${CONTAINER_ID}
fi
CONTAINER_ID=$(docker create diegohermida/telegram_bot:latest_ci);
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
CONTAINER_ID=$(docker create diegohermida/utilities:latest_ci);
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
    exit_with_message 1 "[ERROR] No coverage reports could be fetched in order to generate a merged coverage report." 1;
fi
if (( $SUCCESS_REPORT == 0 )); then
    exit_with_message 1 "[ERROR] No test results reports could be fetched." 1;
fi
message 2 "[SUCCESS] XML test results reports successfully saved to \"./test_results/\"."

# Generating coverage report
message 5 "[ACTION] Generating merged coverage report.";
docker-compose -f docker-compose-ci.yml build --build-arg PATH_TO_REPLACE="$PATH_TO_REPLACE" coverage_ci
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] Report generator image could not be created." 1;
else
    CONTAINER_ID=$(docker create diegohermida/coverage:latest_ci);
    if [ $? != 0 ]; then
        exit_with_message 1 "[ERROR] Report generator container could not be created." 1;
    else
        docker cp ${CONTAINER_ID}:/ClimateChangeApp/code/coverage/coverage.xml ./coverage/coverage.xml;
        if [ $? != 0 ]; then
            SUCCESS_COVERAGE=$((SUCCESS_COVERAGE - 1));
            exit_with_message 1 "[ERROR] Merged coverage report could not be fetched." 1;
        fi
        docker rm ${CONTAINER_ID}
    fi
fi


# Displaying installation summary
echo ""
message 2 "[SUCCESS] Summary:"
message 2 "\t• XML coverage report successfully generated to \"./coverage/coverage.xml\"."
message 2 "\t• XML test reports successfully saved to \"./test_results/\"."
echo ""
