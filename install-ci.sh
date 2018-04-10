#! /bin/bash

# ---------- Functions ---------- #

source "./utilities/bash_util.sh"

# Displays script usage and exits.
# :param $1: Exit code.
function usage () {
    exit_with_message 1 "Installs the application components for CI purposes. This has a few implications:
            \n\t• Docker containers won't expose any port nor volume to the outside.
            \n\t• Docker images's tag will end with \"_ci\". Example: foo/baz:latest_ci.
            \n\t• Docker container's names will end with \"_ci\". Example: foo_ci.
            \n\t• Production containers won't be stopped. This installation won't affect any of them.
            \n\t• Coverage and test result reports will be generated inside the Docker images.
            \n\n> usage: install-ci.sh [-h] [--help] [--version] [--host-ip xxx.xxx.xxx.xxx] [--macos] [--show-ip]
            \n• -h, --help: shows this message
            \n• --version: displays app's version
            \n• --host-ip xxx.xxx.xxx.xxx: specifies the IP address of the machine. By default, this installer attempts
            \n\t  to resolve the machine's IP address. Invoke \"./install.sh --show-ip\" to display the resolved IP address.
            \n• --macos: sets \"docker.for.mac.localhost\" as the local IP address (Docker issue).
            \n• --show-ip: displays the IP address of the machine. If multiple IP's, displays them all." $1;
}


# ---------- Definitions ---------- #

# Setting default values
HOST_IP=$(get_ip_address);
MACOS=false;


# ---------- Argument manipulation ---------- #

# Parsing arguments
EXPECTED_INPUT=":h-:"
while getopts "$EXPECTED_INPUT" ARG; do
    case "${ARG}" in
        h) usage 0 ;;
        -) case ${OPTARG} in
                help) usage 0 ;;
                version) show_app_version ;;
                host-ip)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--host-ip" ${VAL};
                    HOST_IP=${VAL};
                ;;
                macos) MACOS=true ;;
                show-ip) show_ip_addresses ;;
                :) exit_with_message 1 "Illegal option: \"--$OPTARG\" requires an argument" >&2 ;;
                *) exit_with_message 1 "Unrecognized option: --$OPTARG" >&2 ;;
            esac
        ;;
        :) exit_with_message 1 "Illegal option: \"-$OPTARG\" requires an argument" >&2 ;;
        *) exit_with_message 1 "Unrecognized option: -$OPTARG" >&2 ;;
    esac
done


# Overriding IP values if HOST_IP is present
if [ "$MACOS" == "true" ]; then
    message -1 "[INFO] Setting HOST_IP to \"docker.for.mac.localhost\".";
    HOST_IP="docker.for.mac.localhost";
fi
export HOST_IP=${HOST_IP};
message -1 "[INFO] Deploying all components to the local machine. HOST_IP has been set to \"$HOST_IP\".";
message 3 "Hint: If the value of HOST_IP is incorrect, you can override it by invoking: \"./install.sh HOST_IP=<IP>\".";


# Setting CI deploy arguments
DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--all --with-test-reports";
API_DEPLOY_ARGS="--all --with-test-reports";
DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--all --with-test-reports";
TELEGRAM_CONFIGURATOR_DEPLOY_ARGS="--with-test-reports";
UTILITIES_DEPLOY_ARGS="--with-test-reports";


# Setting CI values for ports
export MONGODB_PORT=27018;
export API_PORT=5001;
export POSTGRES_PORT=5433;

# Setting CI bind IP address
export BIND_IP_ADDRESS='127.0.0.1'
message 3 "[WARNING] Docker containers will not be reachable from the Internet. Binding connections to IP address: $BIND_IP_ADDRESS";


# ---------- Installation ---------- #

message 5 "[ACTION] Creating Docker CI containers. Application containers will not be affected.";

# MongoDB component
message 4 "[COMPONENT] MongoDB";

# Deleting the MongoDB service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=mongodb_ci)" ]; then
    message -1 "[INFO] Removing previous MongoDB CI container.";
    docker stop mongodb_ci;
    docker rm mongodb_ci;
fi

# Launching the MongoDB service
message -1 "[INFO] Launching the MongoDB CI service.";
docker-compose -f docker-compose-ci.yml up -d mongodb_ci;
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The MongoDB CI service could not be initialized." 1;
fi


# PostgreSQL component
message 4 "[COMPONENT] PostgreSQL";

# Deleting the PostgreSQL service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=postgres_ci)" ]; then
    message -1 "[INFO] Removing previous PostgreSQL CI container.";
    docker stop postgres_ci;
    docker rm postgres_ci;
fi

# Launching the PostgreSQL service
message -1 "[INFO] Launching the PostgreSQL CI service.";
docker-compose -f docker-compose-ci.yml up -d postgres_ci;
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The PostgreSQL CI service could not be initialized." 1;
fi


# Telegram Configurator component
message 4 "[COMPONENT] Telegram Configurator";

# Building the Telegram Configurator component
docker-compose -f docker-compose-ci.yml build \
                     --build-arg DEPLOY_ARGS="${TELEGRAM_CONFIGURATOR_DEPLOY_ARGS}" telegram_bot_ci;
if [ $? != 0 ]; then
    exit_with_message 1 "> The Telegram Configurator CI image could not be built." 1;
fi


# Utilities component
message 4 "[COMPONENT] Utilities";
docker-compose -f docker-compose-ci.yml build \
                     --build-arg MONGODB_IP=${HOST_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg POSTGRES_IP=${HOST_IP} --build-arg POSTGRES_PORT=${POSTGRES_PORT} \
                     --build-arg DEPLOY_ARGS="${UTILITIES_DEPLOY_ARGS}" utilities_ci;

if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The Utilities CI component could not be built." 1;
fi


# Data Gathering Subsystem component
message 4 "[COMPONENT] Data Gathering Subsystem";

# Building the Data Gathering Subsystem component
docker-compose -f docker-compose-ci.yml build \
                     --build-arg MONGODB_IP=${HOST_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS}" data_gathering_subsystem_ci;
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Gathering Subsystem CI image could not be built." 1;
fi


# API component
message 4 "[COMPONENT] API";

# Deleting the API service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=api_ci)" ]; then
    message -1 "[INFO] Removing previous API CI container.";
    docker stop api_ci;
    docker rm api_ci;
fi

# Building the API service
message -1 "[INFO] Building the API CI image."
docker-compose -f docker-compose-ci.yml build \
                     --build-arg MONGODB_IP=${HOST_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg DEPLOY_ARGS="${API_DEPLOY_ARGS}" api_ci;
if [ $? != 0 ]; then
    exit_with_message 1 "[INFO] The API CI image could not be built." 1;
fi
docker-compose -f docker-compose-ci.yml up -d api_ci;


# Data Conversion Subsystem component
message 4 "[COMPONENT] Data Conversion Subsystem";

# Building the Data Conversion Subsystem component
docker-compose -f docker-compose-ci.yml build \
                     --build-arg POSTGRES_IP=${HOST_IP} --build-arg POSTGRES_PORT=${POSTGRES_PORT} \
                     --build-arg API_IP=${HOST_IP} --build-arg API_PORT=${API_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS}" data_conversion_subsystem_ci;
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Conversion Subsystem CI image could not be built." 1;
fi


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results (CI):";
message 2 "\t• API: built";
message 2 "\t• Data Conversion Subsystem: built";
message 2 "\t• Data Gathering Subsystem: built";
message 2 "\t• MongoDB: up";
message 2 "\t• PostgreSQL: up";
echo "";
