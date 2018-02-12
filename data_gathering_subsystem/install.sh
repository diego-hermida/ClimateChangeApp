#! /bin/bash

# ---------- Definitions ---------- #

# Setting default values
LOCALHOST_IP=null;
SKIP_DEPLOY=true;
DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS=null;

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
            LOCALHOST_IP)                           LOCALHOST_IP=${VALUE} ;;
            SKIP_DEPLOY)                            SKIP_DEPLOY=${VALUE} ;;
            DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS)   DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS=${VALUE} ;;
            *)
    esac
done

# Setting variables to lower case
SKIP_DEPLOY=echo "$SKIP_DEPLOY" | tr '[:upper:]' '[:lower:]';
DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS=echo "$DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS" | tr '[:upper:]' '[:lower:]';

# Warnings
if [ "$DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS" != "null" ] && [ "$SKIP_DEPLOY" == "true" ]; then
    message 3 "[WARNING] Parameter DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS has been set, but SKIP_DEPLOY is true. The
              value will be overridden to \"--skip-all\".";
    DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--skip-all";
    elif [ "$DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS" == "null" ]; then
        message -1 "[INFO] Using default values for DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS.";
        DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
fi

# Ensuring variables contain legit values
if [ "$LOCALHOST_IP" == "null" ] || ([ "$SKIP_DEPLOY" != "true" ] && [ "$SKIP_DEPLOY" != "false" ]); then
     exit_with_message 1 "> usage: install.sh LOCALHOST_IP=xxx.xxx.xxx.xxx [SKIP_DEPLOY=false]
                         [RUN_API=true] [API_BUILD_ARGS=<args>] [DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS=<args>]
                         \n\t- SKIP_DEPLOY takes the value \"true\" by default (affects all components but MongoDB)
                         \n\t- DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS takes the value \"--all --with-tests\" by default
                         \nIMPORTANT: DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS parameter require to use SKIP_DEPLOY=false." 1;
fi


# ---------- Installation ---------- #

# MongoDB component
message 4 "[COMPONENT] Building and launching the MongoDB service.";

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
    exit_with_message 1 "[ERROR] The MongoDB service could not be initialized." $?;
fi


# Data Gathering Subsystem component
message 4 "[COMPONENT] Building the Data Gathering Subsystem.";

# Building the Data Gathering Subsystem component
docker-compose build --build-arg LOCALHOST_IP=${LOCALHOST_IP} --build-arg DEPLOY_ARGS="${DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS}" data_gathering_subsystem
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Gathering Subsystem image could not be built." $?;
fi


# Displaying installation summary
message 2 "[SUCCESS] Installation results:";
message 2 "- MongoDB: up";
message 2 "- Data Gathering Subsystem: built";
echo "";