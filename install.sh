#! /bin/bash

# ---------- Definitions ---------- #

# Setting default values
LOCALHOST_IP=null;
SKIP_DEPLOY=false;

# Exits the installation process, but prints a message to command line before doing so.
# :param $1: Colour of the output line. This will be reset before exiting.
#            If this value equals -1, the default color is used.
# :param $2: Message to be printed.
# :param $3: Exit code.
function exit_with_message () {
    if [ $1 != -1 ]
        then
            tput setaf $1;
    fi
    tput bold;
    echo $2;
    tput sgr0;
    echo ""
    exit $3;
}

# ---------- Installation ---------- #

# Parsing arguments
for ARGUMENT in "$@"
do
    KEY=$(echo $ARGUMENT | cut -f1 -d=)
    VALUE=$(echo $ARGUMENT | cut -f2 -d=)
    case "$KEY" in
            LOCALHOST_IP)   LOCALHOST_IP=${VALUE} ;;
            SKIP_DEPLOY)    SKIP_DEPLOY=${VALUE} ;;
            *)
    esac
done

# Setting variable to lower case
SKIP_DEPLOY=echo "$SKIP_DEPLOY" | tr '[:upper:]' '[:lower:]';

# Ensuring variables contain legit values
if [ "$LOCALHOST_IP" = "null" ] || ([ "$SKIP_DEPLOY" != "true" ] && [ "$SKIP_DEPLOY" != "false" ])
    then
        exit_with_message 1 "> usage: install.sh LOCALHOST_IP=xxx.xxx.xxx.xxx [SKIP_DEPLOY={true|false}]" 1;
fi


# Deleting the MongoDB service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=mongodb)" ]; then
    tput bold;
    echo "> Removing previous MongoDB container."
    tput sgr0;
    docker stop mongodb
    docker rm mongodb
fi

# Launching the MongoDB service
tput bold;
echo "> Launching the MongoDB service."
tput sgr0;
docker-compose up -d mongodb
if [ $? != 0 ]
    then
        exit_with_message 1 "> The Data Gathering Subsystem could not be built." $?;
fi

# Building the Subsystem component
tput bold;
echo "> Building the Data Gathering Subsystem."
tput sgr0;
docker-compose build --build-arg LOCALHOST_IP=${LOCALHOST_IP} --build-arg SKIP_DEPLOY=${SKIP_DEPLOY} subsystem
if [ $? != 0 ]
    then
        exit_with_message 1 "> The Data Gathering Subsystem could not be built." $?;
fi

# Displaying success message
echo ""
exit_with_message 4 "> The Data Gathering Subsystem has been successfully built." 0;