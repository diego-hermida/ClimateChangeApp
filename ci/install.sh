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

HOST_IP=$(calculate_ip_address)
MACOS=false;
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
            -h)             SHOW_HELP=true ;;
            --help)         SHOW_HELP=true ;;
            FORCE_BUILD)    FORCE_BUILD=${VALUE} ;;
            MACOS)          MACOS=${VALUE} ;;
            HOST_IP)        HOST_IP=${VALUE} ;;
            ROOT_DIR)       ROOT_DIR=${VALUE} ;;
            *)
    esac
done


# Showing help if required
if  [ "$SHOW_HELP" == "true" ] || ([ "$MACOS" != "true" ] && [ "$MACOS" != "false" ]) ||
            ([ "$FORCE_BUILD" != "true" ] && [ "$FORCE_BUILD" != "false" ]); then
     exit_with_message 1 "> usage: install.sh [HOST_IP=xxx.xxx.xxx.xxx] [MACOS={true|false}] [ROOT_DIR=<path>]
                            [FORCE_BUILD={true|false}]
            \n\t- -h, --help: shows this message
            \n\t- HOST_IP: IP address of the machine. Defaults to the current IP value of the machine.
            \n\t- MACOS: if set, indicates that \"docker.for.mac.localhost\" should be used instead of the
                   local IP address.
            \n\t- ROOT_DIR: installs the CI components under a custom directory. Defaults to
                  \"~/ClimateChangeApp\".
            \n\t- FORCE_BUILD: builds the CI components' images even if they already exist. Defaults to \"false\"." 1;
fi


# Overriding IP values if HOST_IP is present
if [ "$MACOS" == "true" ]; then
    message -1 "[INFO] Since host OS is macOS/OS X, setting HOST_IP to \"docker.for.mac.localhost\".";
    HOST_IP="docker.for.mac.localhost";
fi
export HOST_IP=${HOST_IP}
message -1 "[INFO] Deploying Jenkins and Sonar components to the local machine. HOST_IP has been set to \"$HOST_IP\".";
message 3 "Hint: If the value of HOST_IP is incorrect, you can override it by invoking: \"./install.sh HOST_IP=<IP>\".";


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