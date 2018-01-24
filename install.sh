#! /bin/bash

# Setting default values
LOCALHOST_IP=null;
SKIP_DEPLOY=false;

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
        tput setaf 1;
        tput bold;
        echo "> usage: install.sh LOCALHOST_IP=xxx.xxx.xxx.xxx [SKIP_DEPLOY={true|false}]";
        tput sgr0;
        echo ""
        exit 1;
fi

# Launching the MongoDB service
tput bold;
echo "> Launching the MongoDB service."
tput sgr0;
docker-compose up -d mongodb
if [ $? != 0 ]
    then
        tput setaf 1;
        tput bold;
        echo "> The Data Gathering Subsystem could not be built.";
        tput sgr0;
        echo ""
        exit $?;
fi

# Building the Subsystem component
tput bold;
echo "> Building the Data Gathering Subsystem."
tput sgr0;
docker-compose build --build-arg LOCALHOST_IP=${LOCALHOST_IP} --build-arg SKIP_DEPLOY=${SKIP_DEPLOY} subsystem
if [ $? != 0 ]
    then
        tput setaf 1;
        tput bold;
        echo "> The Data Gathering Subsystem could not be built.";
        tput sgr0;
        echo ""
        exit $?;
fi

# Displaying success message
tput setaf 4;
tput bold;
echo $'\n> The Data Gathering Subsystem has been successfully built.';
tput sgr0;
echo "";