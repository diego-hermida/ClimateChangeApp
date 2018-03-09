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


# ---------- Definitions ---------- #

FORCE_BUILD=false;
ROOT_DIR="~/ClimateChangeApp";
SHOW_HELP=false;

# ---------- Argument manipulation ---------- #

# Parsing arguments
for ARGUMENT in "$@"
do
    KEY=$(echo ${ARGUMENT} | cut -f1 -d=)
    VALUE=$(echo ${ARGUMENT} | cut -f2 -d=)
    case "$KEY" in
            -h)                 SHOW_HELP=true ;;
            --help)             SHOW_HELP=true ;;
            ROOT_DIR)   ROOT_DIR=${VALUE} ;;
            *)
    esac
done


# Setting variables to lower case


# Ensuring variables contain legit values
if  [ "$SHOW_HELP" == "true" ]; then
     exit_with_message 1 "> usage: install.sh [ROOT_DIR=<path>] [FORCE_BUILD={true|false}]
         \n\t- ROOT_DIR: installs the Jenkins server under a custom directory. Defaults to
               \"~/ClimateChangeApp\".
         \n\t- FORCE_BUILD: builds the Jenkins image even if it already exists. Defaults to \"false\"." 0;
fi


# Overriding default ROOT_DIR?
if [ "$ROOT_DIR" != "~/ClimateChangeApp" ]; then
    message -1 "[INFO] Deploying the Jenkins server under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";


# ---------- Installation ---------- #

# Jenkins component
message 4 "[COMPONENT] Building and launching the Jenkins service.";

# Deleting the Jenkins service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name="jenkins")" ]; then
    message -1 "[INFO] Removing previous Jenkins container.";
    docker stop jenkins;
    docker rm jenkins;
fi
# Launching the Jenkins service
message -1 "[INFO] Launching the Jenkins service.";
if [ "$FORCE_BUILD" == "true" ]; then
    message -1 "[INFO] Recreating Jenkins image.";
    docker-compose up -d --build jenkins;
else
    docker-compose up -d --build jenkins;
fi
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The Jenkins service could not be initialized." 1;
fi


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
exit_with_message 2 "- Jenkins: up" 0