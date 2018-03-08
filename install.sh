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




# ---------- Definitions ---------- #

# Setting default values
MONGODB_IP=null;
POSTGRES_IP=null;
API_IP=null;
LOCALHOST_IP=$(calculate_ip_address);
EXTERNAL_MONGODB_SERVER=false;
EXTERNAL_POSTGRES_SERVER=false;
EXTERNAL_API_SERVICE=false;
RUN_API=false;
SKIP_DEPLOY=true;
MACOS=false;


# ---------- Argument manipulation ---------- #

# Parsing arguments
for ARGUMENT in "$@"
do
    KEY=$(echo $ARGUMENT | cut -f1 -d=)
    VALUE=$(echo $ARGUMENT | cut -f2 -d=)
    case "$KEY" in
            MONGODB_IP)                 MONGODB_IP=${VALUE} ;;
            SKIP_DEPLOY)                SKIP_DEPLOY=${VALUE} ;;
            EXTERNAL_MONGODB_SERVER)    EXTERNAL_MONGODB_SERVER=${VALUE} ;;
            RUN_API)                    RUN_API=${VALUE} ;;
            POSTGRES_IP)                POSTGRES_IP=${VALUE} ;;
            EXTERNAL_POSTGRES_SERVER)   EXTERNAL_POSTGRES_SERVER=${VALUE} ;;
            API_IP)                     API_IP=${VALUE} ;;
            EXTERNAL_API_SERVICE)       EXTERNAL_API_SERVICE=${VALUE} ;;
            LOCALHOST_IP)               LOCALHOST_IP=${VALUE} ;;
            MACOS)                      MACOS=${VALUE} ;;
            *)
    esac
done


# Setting variables to lower case
EXTERNAL_MONGODB_SERVER=echo "$EXTERNAL_MONGODB_SERVER" | tr '[:upper:]' '[:lower:]';
EXTERNAL_POSTGRES_SERVER=echo "$EXTERNAL_POSTGRES_SERVER" | tr '[:upper:]' '[:lower:]';
EXTERNAL_API_SERVICE=echo "$EXTERNAL_API_SERVICE" | tr '[:upper:]' '[:lower:]';
RUN_API=echo "$RUN_API" | tr '[:upper:]' '[:lower:]';
SKIP_DEPLOY=echo "$SKIP_DEPLOY" | tr '[:upper:]' '[:lower:]';
MACOS=echo "$MACOS" | tr '[:upper:]' '[:lower:]';


# Ensuring variables contain legit values

if  ([ "$MONGODB_IP$API_IP$MONGODB_IP" != "nullnullnull" ] && [ "$MONGODB_IP$API_IP$MONGODB_IP" == *"null"* ])
    ([ "$SKIP_DEPLOY" != "true" ] && [ "$SKIP_DEPLOY" != "false" ]) ||
    ([ "$RUN_API" != "true" ] && [ "$RUN_API" != "false" ]) ||
    ([ "$MACOS" != "true" ] && [ "$MACOS" != "false" ]) ||
    ([ "$EXTERNAL_MONGODB_SERVER" != "true" ] && [ "$EXTERNAL_MONGODB_SERVER" != "false" ]) ||
    ([ "$EXTERNAL_API_SERVICE" != "true" ] && [ "$EXTERNAL_API_SERVICE" != "false" ]) ||
    ([ "$EXTERNAL_POSTGRES_SERVER" != "true" ] && [ "$EXTERNAL_POSTGRES_SERVER" != "false" ]); then
         exit_with_message 1 "> usage:
                         \n> install.sh MONGODB_IP=xxx.xxx.xxx.xxx [EXTERNAL_MONGODB_SERVER=true]
                          POSTGRES_IP=xxx.xxx.xxx.xxx [EXTERNAL_POSTGRES_SERVER=true] API_IP=xxx.xxx.xxx.xxx
                          [EXTERNAL_API_SERVICE=true] [RUN_API=true] [SKIP_DEPLOY=false]
                         \n\t- MONGODB_IP: IP address of the machine containing the MongoDB service.
                         \n\t- EXTERNAL_MONGODB_SERVER: indicates that the MongoDB server is externally provided,
                               and does not create a Docker container. Defaults to \"false\".
                         \n\t- POSTGRES_IP: IP address of the machine containing the PostgreSQL service.
                         \n\t- EXTERNAL_POSTGRES_SERVER: indicates that the PostgreSQL server is externally provided,
                               and does not create a Docker container. Defaults to \"false\".
                         \n\t- API_IP: IP address of the machine containing the Data Gathering Subsystem's API service.
                         \n\t- EXTERNAL_API_SERVICE: indicates that the API service is externally provided, and does
                               not create a Docker container. Defaults to \"false\".
                         \n\t- RUN_API: launches the API service after building it. Defaults to \"false\".
                         \n\t- SKIP_DEPLOY: omits all deploy steps. Defaults to \"true\".
                         \n\n> install.sh [MACOS=true] [RUN_API=true] [SKIP_DEPLOY=false]
                         \n\t- MACOS: if set, indicates that \"docker.for.mac.localhost\" should be used instead of the
                               IP address.
                         \n\t- RUN_API: launches the API service after building it. Defaults to \"false\".
                         \n\t- SKIP_DEPLOY: omits all deploy steps. Defaults to \"true\".
                         \n\tNOTE: This option allows to deploy all the Subsystems at the same machine.
                         \n\tIMPORTANT. The \"LOCALHOST_IP\" parameter overrides the values of all \"*_IP\" parameters." 1;
fi


# Overriding IP values if LOCALHOST_IP is present
if [ "$MONGODB_IP$API_IP$MONGODB_IP" == "nullnullnull" ]; then
    message -1 "[INFO] Making a local installation.";
    message -1 "[INFO] The MongoDB, API and PostgreSQL components will be installed (locally) as Docker containers.";
    if [ "$MACOS" == "true" ]; then
        message -1 "[INFO] Since host OS is macOS/OS X, setting LOCALHOST_IP to \"docker.for.mac.localhost.\"."
        LOCALHOST_IP="docker.for.mac.localhost"
    fi
    MONGODB_IP=${LOCALHOST_IP};
    API_IP=${LOCALHOST_IP};
    POSTGRES_IP=${LOCALHOST_IP};
    EXTERNAL_MONGODB_SERVER=false;
    EXTERNAL_POSTGRES_SERVER=false;
    EXTERNAL_API_SERVICE=false;
fi


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


# ---------- Installation ---------- #

# MongoDB component
message 4 "[COMPONENT] Building and launching the MongoDB service.";

if [ "$EXTERNAL_MONGODB_SERVER" == "false" ]; then
    # Deleting the MongoDB service if it was already been created: Brand-new container.
    if [ "$(docker ps -aq -f name=mongodb)" ]; then
        message -1 "[INFO] Removing previous MongoDB container.";
        docker stop mongodb;
        docker rm mongodb;
    fi
    # Launching the MongoDB service
    message -1 "[INFO] Launching the MongoDB service.";
    docker-compose up -d mongodb;
    if [ $? != 0 ]; then
        exit_with_message 1 "[ERROR] The MongoDB service could not be initialized." 1;
    fi
else
    message -1 "[INFO] MongoDB server has been tagged as \"external\". Thus, the MongoDB Docker service won't be launched.";
fi


# Data Gathering Subsystem component
message 4 "[COMPONENT] Building the Data Gathering Subsystem.";

# Building the Data Gathering Subsystem component
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg DEPLOY_ARGS="${DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS}" data_gathering_subsystem
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Gathering Subsystem image could not be built." 1;
fi


# API component
if [ "$EXTERNAL_API_SERVICE" == "false" ]; then
    message 4 "[COMPONENT] Building and (optionally) launching the API service.";
    # Deleting the API service if it was already been created: Brand-new container.
    if [ "$(docker ps -aq -f name=data_gathering_subsystem_api)" ]; then
        message -1 "[INFO] Removing previous API container.";
        docker stop data_gathering_subsystem_api;
        docker rm data_gathering_subsystem_api;
    fi
    # Building the API service
    message -1 "[INFO] Building the API image."
    docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg DEPLOY_ARGS="${API_DEPLOY_ARGS}" api
    if [ $? != 0 ]; then
        exit_with_message 1 "[INFO] The API image could not be built." 1;
    fi
    # Launching the API service
    if [ "$RUN_API" == "true" ]; then
        message -1 "[INFO] Launching the API service.";
        docker-compose up -d api;
        if [ $? != 0 ]; then
            exit_with_message 1 "> The API service could not be initialized." 1;
        fi
    fi
else
     message -1 "[INFO] API service has been tagged as \"external\". Thus, the API Docker service won't be launched.";
fi


# PostgreSQL component
message 4 "[COMPONENT] Building and launching the PostgreSQL service.";

if [ "$EXTERNAL_POSTGRES_SERVER" == "false" ]; then
    # Deleting the MongoDB service if it was already been created: Brand-new container.
    if [ "$(docker ps -aq -f name=postgres)" ]; then
        message -1 "[INFO] Removing previous PostgreSQL container.";
        docker stop postgres;
        docker rm postgres;
    fi
    # Launching the MongoDB service
    message -1 "[INFO] Launching the PostgreSQL service.";
    docker-compose up -d postgres;
    if [ $? != 0 ]; then
        exit_with_message 1 "[ERROR] The PostgreSQL service could not be initialized." 1;
    fi
else
    message -1 "[INFO] PostgreSQL server has been tagged as \"external\". Thus, the PostgreSQL Docker service won't be launched.";
fi


# Data Conversion Subsystem component
message 4 "[COMPONENT] Building the Data Conversion Subsystem.";

# Building the Data Gathering Subsystem component
docker-compose build --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg API_IP=${API_IP} --build-arg DEPLOY_ARGS="${DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS}" data_conversion_subsystem
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Conversion Subsystem image could not be built." 1;
fi


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
if [ "$EXTERNAL_API_SERVICE" == "true" ]; then
    message 2 "- API: external";
    elif [ "$RUN_API" == "true" ]; then
         message 2 "- API: up";
    else message 2 "- API: built";
fi
message 2 "- Data Conversion Subsystem: built";
message 2 "- Data Gathering Subsystem: built";
if [ "$EXTERNAL_MONGODB_SERVER" == "true" ]; then
    message 2 "- MongoDB: external";
    else message 2 "- MongoDB: up";
fi
if [ "$EXTERNAL_POSTGRES_SERVER" == "true" ]; then
    message 2 "- PostgreSQL: external";
    else message 2 "- PostgreSQL: up";
fi
echo "";
