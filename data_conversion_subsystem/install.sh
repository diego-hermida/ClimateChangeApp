#! /bin/bash

# ---------- Definitions ---------- #

# Setting default values
POSTGRES_IP=null;
API_IP=null;
EXTERNAL_POSTGRES_SERVER=false;
SKIP_DEPLOY=true;

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
            SKIP_DEPLOY)                SKIP_DEPLOY=${VALUE} ;;
            POSTGRES_IP)                POSTGRES_IP=${VALUE} ;;
            EXTERNAL_POSTGRES_SERVER)   EXTERNAL_POSTGRES_SERVER=${VALUE} ;;
            API_IP)                     API_IP=${VALUE} ;;
            *)
    esac
done


# Setting variables to lower case
EXTERNAL_POSTGRES_SERVER=echo "$EXTERNAL_POSTGRES_SERVER" | tr '[:upper:]' '[:lower:]';
SKIP_DEPLOY=echo "$SKIP_DEPLOY" | tr '[:upper:]' '[:lower:]';


# Ensuring variables contain legit values

if [ "$API_IP" == "null" ] || [ "$POSTGRES_IP" == "null" ] ||
    ([ "$SKIP_DEPLOY" != "true" ] && [ "$SKIP_DEPLOY" != "false" ]) ||
    ([ "$EXTERNAL_POSTGRES_SERVER" != "true" ] && [ "$EXTERNAL_POSTGRES_SERVER" != "false" ]); then
         exit_with_message 1 "> usage:
                         \n> install.sh API_IP=xxx.xxx.xxx.xxx POSTGRES_IP=xxx.xxx.xxx.xxx [EXTERNAL_POSTGRES_SERVER=true]
                         [SKIP_DEPLOY=false]
                         \n\t- API_IP: IP address of the machine containing the Data Gathering Subsystem's API service.
                         \n\t- POSTGRES_IP: IP address of the machine containing the PostgreSQL service.
                         \n\t- EXTERNAL_POSTGRES_SERVER: indicates that the PostgreSQL server is externally provided,
                               and does not create a Docker container. Defaults to \"false\".
                         \n\t- SKIP_DEPLOY: omits all deploy steps. Defaults to \"true\".
                         \n\t- DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS: enables \"Expert Mode\", allowing to pass custom
                               args to the deploy script. Defaults to \"--all --with-tests\".
                         \nIMPORTANT: DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS must be used in conjunction with
                                      SKIP_DEPLOY=false." 1;
fi


# Warnings
if  [ "$SKIP_DEPLOY" == "true" ]; then
        message -1 "[INFO] Deploy operations will be skipped for the Data Conversion Subsystem component.";
        DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--skip-all";
    else
        message -1 "[INFO] Using default values for DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS.";
        DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
fi


# ---------- Installation ---------- #

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
if [ "$EXTERNAL_POSTGRES_SERVER" == "true" ]; then
    message 2 "- PostgreSQL: external";
    else message 2 "- PostgreSQL: up";
fi
message 2 "- Data Conversion Subsystem: built";
echo "";
