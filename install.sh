#! /bin/bash

# ---------- Functions ---------- #

# Exits the installation process, but prints a message to command line before doing so.
# :param $1: Colour of the output line. This will be reset before exiting.
#            If this value equals -1, the default color is used.
# :param $2: Message to be printed.
# :param $3: Exit code.
function exit_with_message () {
    if [ $1 != -1 ]; then
        tput -T xterm-256color setaf $1;
    fi
    tput -T xterm-256color bold;
    echo -e $2;
    tput -T xterm-256color sgr0;
    echo ""
    exit $3;
}

# Prints a message. Message output uses bold by default.
# :param $1: Colour of the output line. This will be reset before exiting.
#            If this value equals -1, the default color is used.
# :param $2: Message to be printed.
function message () {
    tput -T xterm-256color bold;
    if [ $1 != -1 ]; then
        tput -T xterm-256color setaf $1;
    fi
    echo -e $2
    tput -T xterm-256color sgr0;
}

# Calculates the machine's IPv4 address.
function calculate_ip_address () {
    local _ip _myip _line _nl=$'\n'
    while IFS=$': \t' read -a _line ;do
        [ -z "${_line%inet}" ] &&
           _ip=${_line[${#_line[1]}>4?1:2]} &&
           [ "${_ip#127.0.0.1}" ] && _myip=$_ip
      done< <(LANG=C /sbin/ifconfig)
    printf ${1+-v} $1 "%s${_nl:0:$[${#1}>0?0:1]}" $_myip
}


# ---------- Definitions ---------- #

# Setting default values
HOST_IP=$(calculate_ip_address);
RUN_API=false;
EXPOSE_CONTAINERS=true;
RUN_TELEGRAM=false;
SKIP_DEPLOY=true;
MACOS=false;
ROOT_DIR="~/ClimateChangeApp";
CI=false;

# ---------- Argument manipulation ---------- #

# Parsing arguments
for ARGUMENT in "$@"
do
    KEY=$(echo ${ARGUMENT} | cut -f1 -d=)
    VALUE=$(echo ${ARGUMENT} | cut -f2 -d=)
    case "$KEY" in
            HOST_IP)        HOST_IP=${VALUE} ;;
            RUN_API)        RUN_API=${VALUE} ;;
            EXPOSE_CONTAINERS)     EXPOSE_CONTAINERS=${VALUE} ;;
            SKIP_DEPLOY)    SKIP_DEPLOY=${VALUE} ;;
            MACOS)          MACOS=${VALUE} ;;
            ROOT_DIR)       ROOT_DIR=${VALUE} ;;
            CI)             CI=${VALUE} ;;
            *)
    esac
done


# Setting variables to lower case
RUN_API=echo "$RUN_API" | tr '[:upper:]' '[:lower:]';
EXPOSE_CONTAINERS=echo "$EXPOSE_CONTAINERS" | tr '[:upper:]' '[:lower:]';
RUN_TELEGRAM=echo "$RUN_API" | tr '[:upper:]' '[:lower:]';
SKIP_DEPLOY=echo "$SKIP_DEPLOY" | tr '[:upper:]' '[:lower:]';
MACOS=echo "$MACOS" | tr '[:upper:]' '[:lower:]';
CI=echo "$CI" | tr '[:upper:]' '[:lower:]';


# Ensuring variables contain legit values
if  ([ "$SKIP_DEPLOY" != "true" ] && [ "$SKIP_DEPLOY" != "false" ]) ||
        ([ "$RUN_API" != "true" ] && [ "$RUN_API" != "false" ]) ||
        ([ "$EXPOSE_CONTAINERS" != "true" ] && [ "$EXPOSE_CONTAINERS" != "false" ]) ||
        ([ "$RUN_TELEGRAM" != "true" ] && [ "$RUN_TELEGRAM" != "false" ]) ||
        ([ "$CI" != "true" ] && [ "$CI" != "false" ]) ||
        ([ "$MACOS" != "true" ] && [ "$MACOS" != "false" ]); then
    exit_with_message 1 "> usage:
            \n install.sh [HOST_IP=<IP>] [EXPOSE_CONTAINERS={true|false}] [MACOS={true|false}] [RUN_API={true|false}]
            \n\t\t[RUN_TELEGRAM={true|false}] [SKIP_DEPLOY={true|false}] [ROOT_DIR=<path>] [CI={true|false}]
            \n\t- HOST_IP: IP address of the machine. Defaults to the current IP value of the machine.
            \n\t- EXPOSE_CONTAINERS: exposes Docker containers to the outside (0.0.0.0). Defaults to \"true\".
            \n\t- MACOS: if set, indicates that \"docker.for.mac.localhost\" should be used instead of the
                   local IP address.
            \n\t- RUN_API: launches the API service after building it. Defaults to \"false\".
            \n\t- RUN_TELEGRAM: launches the Telegram Configurator service. Defaults to \"false\".
            \n\t- SKIP_DEPLOY: omits all deploy steps. Defaults to \"true\".
            \n\t- ROOT_DIR: installs the Application under a custom directory. Defaults to
                  \"~/ClimateChangeApp\".
            \n\t- CI: uses CI images, containers and services. Defaults to \"false\".
            \n\tNOTE: This option allows to deploy all the Subsystems to the same machine.
            \n\tIMPORTANT. The \"HOST_IP\" parameter sets the MONGODB_IP, API_IP and POSTGRES_IP parameters." 1;
fi


# CI and default directory?
if ([ "$CI" == "true" ] && [ "$ROOT_DIR" != "~/ClimateChangeApp" ]); then
    message 3 "[WARNING] CI Docker containers do not export any volume. As a result, the ROOT_DIR parameter will be ignored.";
fi


# Overriding IP values if HOST_IP is present
message -1 "[INFO] The application will be installed (locally) using Docker containers.";
if [ "$MACOS" == "true" ]; then
    message -1 "[INFO] Since host OS is macOS/OS X, setting HOST_IP to \"docker.for.mac.localhost\".";
    HOST_IP="docker.for.mac.localhost";
fi
export HOST_IP=${HOST_IP}
message -1 "[INFO] Deploying all components to the local machine. HOST_IP has been set to \"$HOST_IP\".";
message 3 "Hint: If the value of HOST_IP is incorrect, you can override it by invoking: \"./install.sh HOST_IP=<IP>\".";
MONGODB_IP=${HOST_IP};
API_IP=${HOST_IP};
POSTGRES_IP=${HOST_IP};


# Binding containers to local?
if [ "$EXPOSE_CONTAINERS" == "true" ]; then
    message -1 "[INFO] Exposing Docker containers by using the 0.0.0.0 mask.";
    export BIND_IP_ADDRESS='0.0.0.0';
else
     if [ "$HOST_IP" == "docker.for.mac.localhost" ]; then
        export BIND_IP_ADDRESS="127.0.0.1";
     else
        export BIND_IP_ADDRESS=${HOST_IP};
     fi
     message -1 "[INFO] Restricting connections to the HOST_IP address: $HOST_IP.";
     message 3 "[WARNING] Docker containers will not be reachable from the outside.";
fi


# Warnings
if  [ "$SKIP_DEPLOY" == "true" ]; then
    message -1 "[INFO] Deploy operations will be skipped for the API component.";
    message -1 "[INFO] Deploy operations will be skipped for the Data Gathering Subsystem component.";
    message -1 "[INFO] Deploy operations will be skipped for the Data Conversion Subsystem component.";
    message -1 "[INFO] Deploy operations will be skipped for the Telegram Configurator component.";
    message -1 "[INFO] Deploy operations will be skipped for the Utilities component.";
    API_DEPLOY_ARGS="--skip-all";
    DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--skip-all";
    DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--skip-all";
    TELEGRAM_CONFIGURATOR_DEPLOY_ARGS="--skip-all";
    UTILITIES_DEPLOY_ARGS="--skip-all";
elif [ "$CI" == "true" ]; then
    message -1 "[INFO] Adding coverage and test results report generation to API_DEPLOY_ARGS.";
    message -1 "[INFO] Adding coverage and test results report generation to DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS.";
    message -1 "[INFO] Adding coverage and test results report generation to DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS.";
    message -1 "[INFO] Adding coverage and test results report generation to TELEGRAM_CONFIGURATOR_DEPLOY_ARGS.";
    message -1 "[INFO] Adding coverage and test results report generation to UTILITIES_DEPLOY_ARGS.";
    API_DEPLOY_ARGS="--all --with-test-reports";
    DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--all --with-test-reports";
    DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--all --with-test-reports";
    TELEGRAM_CONFIGURATOR_DEPLOY_ARGS="--with-test-reports";
    UTILITIES_DEPLOY_ARGS="--with-test-reports";
else
    message -1 "[INFO] Using default values for API_DEPLOY_ARGS.";
    message -1 "[INFO] Using default values for DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS.";
    message -1 "[INFO] Using default values for DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS.";
    message -1 "[INFO] Using default values for TELEGRAM_CONFIGURATOR_DEPLOY_ARGS.";
    message -1 "[INFO] Using default values for UTILITIES_DEPLOY_ARGS.";
    API_DEPLOY_ARGS="--all --with-tests";
    DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
    DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
    TELEGRAM_CONFIGURATOR_DEPLOY_ARGS="--with-tests";
    UTILITIES_DEPLOY_ARGS="--with-tests";
fi


# Overriding default ROOT_DIR?
if [ "$ROOT_DIR" != "~/ClimateChangeApp" ]; then
    message -1 "[INFO] Deploying the application under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";


# Setting default ports?
if [ "$CI" == "false" ]; then
    MONGODB_PORT=27017;
    POSTGRES_PORT=5432;
    API_PORT=5000;
    message -1 "[INFO] Using default values for MongoDB, PostgreSQL and API ports.";
else
    MONGODB_PORT=27018;
    POSTGRES_PORT=5433;
    API_PORT=5001;
    message -1 "[INFO] Using CI values for MongoDB, PostgreSQL and API ports.";
fi


# Creating CI containers?
if [ "$CI" == "true" ]; then
    message 5 "[ACTION] Creating Docker CI containers. Application containers will not be affected.";
    export CI_EXTENSION="_CI";
else
    export CI_EXTENSION="";
fi


# ---------- Installation ---------- #

# MongoDB component
message 4 "[COMPONENT] Building and launching the MongoDB service.";

# Deleting the MongoDB service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name="mongodb$CI_EXTENSION")" ]; then
    message -1 "[INFO] Removing previous MongoDB$CI_EXTENSION container.";
    docker stop "mongodb$CI_EXTENSION";
    docker rm "mongodb$CI_EXTENSION";
fi
# Launching the MongoDB service
message -1 "[INFO] Launching the MongoDB service.";
docker-compose up -d "mongodb$CI_EXTENSION";
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The MongoDB service could not be initialized." 1;
fi


# PostgreSQL component
message 4 "[COMPONENT] Building and launching the PostgreSQL service.";

# Deleting the PostgreSQL service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name="postgres$CI_EXTENSION")" ]; then
    message -1 "[INFO] Removing previous PostgreSQL$CI_EXTENSION container.";
    docker stop "postgres$CI_EXTENSION";
    docker rm "postgres$CI_EXTENSION";
fi
# Launching the PostgreSQL service
message -1 "[INFO] Launching the PostgreSQL service.";
docker-compose up -d "postgres$CI_EXTENSION";
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The PostgreSQL service could not be initialized." 1;
fi


# Telegram Configurator component
message 4 "[COMPONENT] Building the Telegram Configurator component.";

# Building the Telegram Configurator component
docker-compose build --build-arg DEPLOY_ARGS="${TELEGRAM_CONFIGURATOR_DEPLOY_ARGS}" "telegram_bot$CI_EXTENSION";
if [ $? != 0 ]; then
    exit_with_message 1 "> The Telegram Configurator image could not be built." 1;
fi
# Running the Telegram Configurator component
if [ "$RUN_TELEGRAM" == "true" ]; then
    message -1 "[INFO] Running the Telegram Configurator component.";
    echo "";
    docker run --rm -i -t --name "telegram_bot$CI_EXTENSION" "diegohermida/telegram_bot:latest$CI_EXTENSION";

    # Displaying installation summary
    if [ $? != 0 ]; then
        exit_with_message 1 "\n[ERROR] The Telegram Configurator did not exit normally. You should rerun this installer." 1;
    else
        message 2 "\n[SUCCESS] The Telegram Configurator was successful.";
        exit_with_message -1 "[INFO] The installation will finish now. Be sure to follow the Telegrama Configurator
                    instructions, and restart this installer without RUN_TELEGRAM=true." 0
    fi
fi


# Utilities component
message 4 "[COMPONENT] Building and testing the Utilities component.";
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg POSTGRES_PORT=${POSTGRES_PORT} \
                     --build-arg DEPLOY_ARGS="${UTILITIES_DEPLOY_ARGS}" "utilities$CI_EXTENSION";

if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The Utilities component could not be built." 1;
fi


# Data Gathering Subsystem component
message 4 "[COMPONENT] Building the Data Gathering Subsystem.";

# Building the Data Gathering Subsystem component
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS}" "data_gathering_subsystem$CI_EXTENSION";
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Gathering Subsystem image could not be built." 1;
fi


# API component
if [ "$RUN_API" == "true" ]; then
    message 4 "[COMPONENT] Building and launching the API service.";
else
    message 4 "[COMPONENT] Building the API service.";
fi

# Deleting the API service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name="data_gathering_subsystem_api_CI$CI_EXTENSION")" ]; then
    message -1 "[INFO] Removing previous API$CI_EXTENSION container.";
    docker stop "data_gathering_subsystem_api_CI$CI_EXTENSION";
    docker rm "data_gathering_subsystem_api_CI$CI_EXTENSION";
fi
# Building the API service
message -1 "[INFO] Building the API image."
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg DEPLOY_ARGS="${API_DEPLOY_ARGS}" "api$CI_EXTENSION";
if [ $? != 0 ]; then
    exit_with_message 1 "[INFO] The API image could not be built." 1;
fi
# Launching the API service
if [ "$RUN_API" == "true" ]; then
    message -1 "[INFO] Launching the API service.";
    docker-compose up -d "api$CI_EXTENSION";
    if [ $? != 0 ]; then
        exit_with_message 1 "> The API service could not be initialized." 1;
    fi
fi


# Data Conversion Subsystem component
message 4 "[COMPONENT] Building the Data Conversion Subsystem.";

# Building the Data Conversion Subsystem component
docker-compose build --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg API_IP=${API_IP} \
                     --build-arg POSTGRES_PORT=${POSTGRES_PORT} --build-arg API_PORT=${API_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS}" "data_conversion_subsystem$CI_EXTENSION";
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Conversion Subsystem image could not be built." 1;
fi


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
if [ "$RUN_API" == "true" ]; then
    message 2 "- API$CI_EXTENSION: up";
else
    message 2 "- API$CI_EXTENSION: built";
fi
message 2 "- Data Conversion Subsystem$CI_EXTENSION: built";
message 2 "- Data Gathering Subsystem$CI_EXTENSION: built";
message 2 "- MongoDB$CI_EXTENSION: up";
message 2 "- PostgreSQL$CI_EXTENSION: up";
echo "";
