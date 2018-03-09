#! /bin/bash

# ---------- Functions ---------- #

# Exits the installation process, but prints a message to command line before doing so.
# :param $1: Colour of the output line. This will be reset before exiting.
#            If this value equals -1, the default color is used.
# :param $2: Message to be printed.
# :param $3: Exit code.
function exit_with_message () {
    if [ $1 != -1 ]; then
        tput setaf $1;
    fi
    tput bold;
    echo -e $2;
    tput sgr0;
    echo ""
    exit $3;
}

# Prints a message. Message output uses bold by default.
# :param $1: Colour of the output line. This will be reset before exiting.
#            If this value equals -1, the default color is used.
# :param $2: Message to be printed.
function message () {
    tput bold;
    if [ $1 != -1 ]; then
        tput setaf $1;
    fi
    echo -e $2
    tput sgr0;
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
SKIP_DEPLOY=true;
MACOS=false;
ROOT_PROJECT_DIR="~/ClimateChangeApp";
CI=false;

# ---------- Argument manipulation ---------- #

# Parsing arguments
for ARGUMENT in "$@"
do
    KEY=$(echo ${ARGUMENT} | cut -f1 -d=)
    VALUE=$(echo ${ARGUMENT} | cut -f2 -d=)
    case "$KEY" in
            HOST_IP)            HOST_IP=${VALUE} ;;
            RUN_API)            RUN_API=${VALUE} ;;
            SKIP_DEPLOY)        SKIP_DEPLOY=${VALUE} ;;
            MACOS)              MACOS=${VALUE} ;;
            ROOT_PROJECT_DIR)   ROOT_PROJECT_DIR=${VALUE} ;;
            CI)                 CI=${VALUE} ;;
            *)
    esac
done

# Setting variables to lower case
RUN_API=echo "$RUN_API" | tr '[:upper:]' '[:lower:]';
SKIP_DEPLOY=echo "$SKIP_DEPLOY" | tr '[:upper:]' '[:lower:]';
MACOS=echo "$MACOS" | tr '[:upper:]' '[:lower:]';
CI=echo "$CI" | tr '[:upper:]' '[:lower:]';

# Ensuring variables contain legit values
if  ([ "$SKIP_DEPLOY" != "true" ] && [ "$SKIP_DEPLOY" != "false" ]) ||
    ([ "$RUN_API" != "true" ] && [ "$RUN_API" != "false" ]) ||
    ([ "$MACOS" != "true" ] && [ "$MACOS" != "false" ]); then
         exit_with_message 1 "> usage:
                         \n install.sh [HOST_IP=<IP>][MACOS={true|false}] [RUN_API={true|false}] [SKIP_DEPLOY={true|false}]
                         \n\t\t[ROOT_PROJECT_DIR=<path>] [CI={true|false}]
                         \n\t- MACOS: if set, indicates that \"docker.for.mac.localhost\" should be used instead of the
                               local IP address.
                         \n\t- RUN_API: launches the API service after building it. Defaults to \"false\".
                         \n\t- SKIP_DEPLOY: omits all deploy steps. Defaults to \"true\".
                         \n\t- ROOT_PROJECT_DIR: installs the Application under a custom directory. Defaults to
                               \"~/ClimateChangeApp\".
                         \n\t- CI: uses CI images, containers and services. Defaults to \"false\".
                         \n\tNOTE: This option allows to deploy all the Subsystems to the same machine.
                         \n\tIMPORTANT. The \"HOST_IP\" parameter overrides the values of all \"*_IP\" parameters." 1;
fi

# CI and default directory?
if ([ "$CI" == "true" ] && [ "$ROOT_PROJECT_DIR" == "~/ClimateChangeApp" ]); then
    exit_with_message 1 "[ERROR] Deploying the application under the default directory \"$ROOT_PROJECT_DIR\" is not
                         allowed when invoking \"install.sh <args> CI=true\"." 1;
fi

# Overriding IP values if HOST_IP is present
message -1 "[INFO] The MongoDB, API and PostgreSQL components will be installed (locally) as Docker containers.";
if [ "$MACOS" == "true" ]; then
    message -1 "[INFO] Since host OS is macOS/OS X, setting HOST_IP to \"docker.for.mac.localhost\".";
    HOST_IP="docker.for.mac.localhost";
fi
message -1 "[INFO] Deploying all components to the local machine. HOST_IP has been set to \"$HOST_IP\".";
message 3 "Hint: If the value of HOST_IP is incorrect, you can override it by invoking: \"./install.sh HOST_IP=<IP>\".";
MONGODB_IP=${HOST_IP};
API_IP=${HOST_IP};
POSTGRES_IP=${HOST_IP};

# Warnings
if  [ "$SKIP_DEPLOY" == "true" ]; then
        message -1 "[INFO] Deploy operations will be skipped for the API component.";
        message -1 "[INFO] Deploy operations will be skipped for the Data Gathering Subsystem component.";
        message -1 "[INFO] Deploy operations will be skipped for the Data Conversion Subsystem component.";
        API_DEPLOY_ARGS="--skip-all";
        DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--skip-all";
        DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--skip-all";
else
    message -1 "[INFO] Using default values for API_DEPLOY_ARGS.";
    message -1 "[INFO] Using default values for DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS.";
    message -1 "[INFO] Using default values for DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS.";
    API_DEPLOY_ARGS="--all --with-tests";
    DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
    DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
fi

# Overriding default ROOT_PROJECT_DIR?
if [ "$ROOT_PROJECT_DIR" != "~/ClimateChangeApp" ]; then
    message -1 "[INFO] Deploying the application under custom directory: $ROOT_PROJECT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_PROJECT_DIR.";
fi
export ROOT_PROJECT_DIR="$ROOT_PROJECT_DIR";

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
    message 5 "[ACTION] Creating Docker CI containers. Originals";
    export CI="_CI";
else
    message -1 "[INFO] Using default names for Docker containers.";
    export CI="";
fi


# ---------- Installation ---------- #

# MongoDB component
message 4 "[COMPONENT] Building and launching the MongoDB service.";

# Deleting the MongoDB service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name="mongodb$CI")" ]; then
    message -1 "[INFO] Removing previous MongoDB$CI container.";
    docker stop "mongodb$CI";
    docker rm "mongodb$CI";
fi
# Launching the MongoDB service
message -1 "[INFO] Launching the MongoDB service.";
docker-compose up -d "mongodb$CI";
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The MongoDB service could not be initialized." 1;
fi


# Data Gathering Subsystem component
message 4 "[COMPONENT] Building the Data Gathering Subsystem.";

# Building the Data Gathering Subsystem component
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS}" "data_gathering_subsystem$CI";
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Gathering Subsystem image could not be built." 1;
fi


# API component
message 4 "[COMPONENT] Building and (optionally) launching the API service.";

# Deleting the API service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name="data_gathering_subsystem_api_CI$CI")" ]; then
    message -1 "[INFO] Removing previous API$CI container.";
    docker stop "data_gathering_subsystem_api_CI$CI";
    docker rm "data_gathering_subsystem_api_CI$CI";
fi
# Building the API service
message -1 "[INFO] Building the API image."
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg DEPLOY_ARGS="${API_DEPLOY_ARGS}" "api$CI";
if [ $? != 0 ]; then
    exit_with_message 1 "[INFO] The API image could not be built." 1;
fi
# Launching the API service
if [ "$RUN_API" == "true" ]; then
    message -1 "[INFO] Launching the API service.";
    docker-compose up -d "api$CI";
    if [ $? != 0 ]; then
        exit_with_message 1 "> The API service could not be initialized." 1;
    fi
fi


# PostgreSQL component
message 4 "[COMPONENT] Building and launching the PostgreSQL service.";

# Deleting the MongoDB service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name="postgres$CI")" ]; then
    message -1 "[INFO] Removing previous PostgreSQL$CI container.";
    docker stop "postgres$CI";
    docker rm "postgres$CI";
fi
# Launching the MongoDB service
message -1 "[INFO] Launching the PostgreSQL service.";
docker-compose up -d "postgres$CI";
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The PostgreSQL service could not be initialized." 1;
fi


# Data Conversion Subsystem component
message 4 "[COMPONENT] Building the Data Conversion Subsystem.";

# Building the Data Gathering Subsystem component
docker-compose build --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg API_IP=${API_IP} \
                     --build-arg POSTGRES_PORT=${POSTGRES_PORT} --build-arg API_PORT=${API_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS}" "data_conversion_subsystem$CI";
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Conversion Subsystem image could not be built." 1;
fi


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
if [ "$RUN_API" == "true" ]; then
    message 2 "- API$CI: up";
else
    message 2 "- API$CI: built";
fi
message 2 "- Data Conversion Subsystem$CI: built";
message 2 "- Data Gathering Subsystem$CI: built";
message 2 "- MongoDB$CI: up";
message 2 "- PostgreSQL$CI: up";
echo "";
