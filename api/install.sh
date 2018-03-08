#! /bin/bash

# ---------- Definitions ---------- #

# Setting default values
MONGODB_IP=null;
EXTERNAL_MONGODB_SERVER=false;
SKIP_DEPLOY=true;
RUN_API=false;
API_DEPLOY_ARGS=null;

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

# ---------- Argument manipulation ---------- #

# Parsing arguments
for ARGUMENT in "$@"
do
    KEY=$(echo $ARGUMENT | cut -f1 -d=)
    VALUE=$(echo $ARGUMENT | cut -f2 -d=)
    case "$KEY" in
            MONGODB_IP)                 MONGODB_IP=${VALUE} ;;
            SKIP_DEPLOY)                SKIP_DEPLOY=${VALUE} ;;
            RUN_API)                    RUN_API=${VALUE} ;;
            API_DEPLOY_ARGS)            API_DEPLOY_ARGS=${VALUE} ;;
            EXTERNAL_MONGODB_SERVER)    EXTERNAL_MONGODB_SERVER=${VALUE} ;;
            *)
    esac
done

# Setting variables to lower case
SKIP_DEPLOY=echo "$SKIP_DEPLOY" | tr '[:upper:]' '[:lower:]';
RUN_API=echo "$RUN_API" | tr '[:upper:]' '[:lower:]';
API_DEPLOY_ARGS=echo "$API_DEPLOY_ARGS" | tr '[:upper:]' '[:lower:]';
EXTERNAL_MONGODB_SERVER=echo "$EXTERNAL_MONGODB_SERVER" | tr '[:upper:]' '[:lower:]';

# Warnings
if [ "$API_DEPLOY_ARGS" != "null" ] && [ "$SKIP_DEPLOY" == "true" ]; then
    message 3 "[WARNING] Parameter API_DEPLOY_ARGS has been set, but SKIP_DEPLOY is true. The value will be overridden
              to \"--skip-all\".";
    elif [ "$SKIP_DEPLOY" == "true" ]; then
        message -1 "[INFO] Deploy operations will be skipped for the API component.";
        API_DEPLOY_ARGS="--skip-all"
    elif [ "$API_DEPLOY_ARGS" == "null" ]; then
        message -1 "[INFO] Using default values for API_DEPLOY_ARGS.";
        API_DEPLOY_ARGS="--all --with-tests";
fi

# Ensuring variables contain legit values
if [ "$MONGODB_IP" == "null" ] || ([ "$SKIP_DEPLOY" != "true" ] && [ "$SKIP_DEPLOY" != "false" ]) ||
        ([ "$RUN_API" != "true" ] && [ "$RUN_API" != "false" ]) ||
        ([ "$EXTERNAL_MONGODB_SERVER" != "true" ] && [ "$EXTERNAL_MONGODB_SERVER" != "false" ]); then
     exit_with_message 1 "> usage: install.sh MONGODB_IP=xxx.xxx.xxx.xxx [EXTERNAL_MONGODB_SERVER=true] [SKIP_DEPLOY=false]
                         [RUN_API=true] [API_DEPLOY_ARGS=<args>]
                         \n\t- MONGODB_IP: IP address of the machine containing the MongoDB service.
                         \n\t- EXTERNAL_MONGODB_SERVER: indicates that the MongoDB server is externally provided,
                               and does not create a Docker container. Defaults to \"false\".
                         \n\t- SKIP_DEPLOY: omits all deploy steps. Defaults to \"true\".
                         \n\t- RUN_API: launches the API service after building it. Defaults to \"false\".
                         \n\t- API_DEPLOY_ARGS: enables \"Expert Mode\", allowing to pass custom args to the deploy
                               script. Defaults to \"--all --with-tests\".
                         \nIMPORTANT: API_DEPLOY_ARGS must be used in conjunction with SKIP_DEPLOY=false." 1;
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

# API component
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


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
if [ "$EXTERNAL_MONGODB_SERVER" == "true" ]; then
    message 2 "- MongoDB: external";
    else message 2 "- MongoDB: up";
fi
if [ "$RUN_API" == "true" ]; then
    message 2 "- API: built & up";
    else message 2 "- API: built";
fi
echo "";
