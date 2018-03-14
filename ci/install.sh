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
            -h)         SHOW_HELP=true ;;
            --help)     SHOW_HELP=true ;;
            ROOT_DIR)   ROOT_DIR=${VALUE} ;;
            *)
    esac
done


# Showing help if required
if  [ "$SHOW_HELP" == "true" ]; then
     exit_with_message 1 "> usage: install.sh [ROOT_DIR=<path>] [FORCE_BUILD={true|false}]
            \n\t- -h, --help: shows this message
            \n\t- ROOT_DIR: installs the CI components under a custom directory. Defaults to
                  \"~/ClimateChangeApp\".
            \n\t- FORCE_BUILD: builds the CI components' images even if they already exist. Defaults to \"false\"." 0;
fi


# Overriding default ROOT_DIR?
if [ "$ROOT_DIR" != "~/ClimateChangeApp" ]; then
    message -1 "[INFO] Deploying the Jenkins server under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";


# Making Jenkins and SonarQube accessible from any host
export BIND_IP_ADDRESS="0.0.0.0"


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
    docker-compose up -d jenkins;
fi
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The Jenkins service could not be initialized." 1;
fi


# Sonar component
message 4 "[COMPONENT] Building and launching the Sonar service.";

# Deleting the Sonar service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name="sonar")" ]; then
    message -1 "[INFO] Removing previous Sonar containers.";
    docker rm --force sonar;
    docker rm --force sonar_db;
fi
# Launching the Sonar service
message -1 "[INFO] Launching the Sonar service.";
if [ "$FORCE_BUILD" == "true" ]; then
    message -1 "[INFO] Recreating Sonar image.";
    docker-compose up -d --build sonar;
else
    docker-compose up -d sonar;
fi
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The Sonar service could not be initialized." 1;
fi

# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
message 2 "- Jenkins: up"
message 2 "- Sonar: up"
message 2 "- Sonar (db): up"
echo ""