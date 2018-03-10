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

# Setting default values
POSTGRES_IP=$(calculate_ip_address);
API_IP=$(calculate_ip_address);
EXTERNAL_POSTGRES_SERVER=false;
SKIP_DEPLOY=true;
MACOS=false;
ROOT_DIR="~/ClimateChangeApp";


# ---------- Argument manipulation ---------- #

# Parsing arguments
for ARGUMENT in "$@"
do
    KEY=$(echo $ARGUMENT | cut -f1 -d=)
    VALUE=$(echo $ARGUMENT | cut -f2 -d=)
    case "$KEY" in
            SKIP_DEPLOY)                            SKIP_DEPLOY=${VALUE} ;;
            POSTGRES_IP)                            POSTGRES_IP=${VALUE} ;;
            EXTERNAL_POSTGRES_SERVER)               EXTERNAL_POSTGRES_SERVER=${VALUE} ;;
            DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS)  DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS=${VALUE} ;;
            API_IP)                                 API_IP=${VALUE} ;;
            MACOS)                                  MACOS=${VALUE} ;;
            ROOT_DIR)                               ROOT_DIR=${VALUE} ;;
            *)
    esac
done


# Setting variables to lower case
EXTERNAL_POSTGRES_SERVER=echo "$EXTERNAL_POSTGRES_SERVER" | tr '[:upper:]' '[:lower:]';
SKIP_DEPLOY=echo "$SKIP_DEPLOY" | tr '[:upper:]' '[:lower:]';
MACOS=echo "$MACOS" | tr '[:upper:]' '[:lower:]';

# Ensuring variables contain legit values

if [ "$API_IP" == "null" ] || [ "$POSTGRES_IP" == "null" ] ||
        ([ "$SKIP_DEPLOY" != "true" ] && [ "$SKIP_DEPLOY" != "false" ]) ||
        ([ "$EXTERNAL_POSTGRES_SERVER" != "true" ] && [ "$EXTERNAL_POSTGRES_SERVER" != "false" ]) ||
        ([ "$MACOS" != "true" ] && [ "$MACOS" != "false" ]); then
     exit_with_message 1 "> usage:
            \n> install.sh [API_IP=xxx.xxx.xxx.xxx] [POSTGRES_IP=xxx.xxx.xxx.xxx] [EXTERNAL_POSTGRES_SERVER={true|false}]
            [SKIP_DEPLOY={true|false}] [DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS=<args>] [MACOS={true|false}] [ROOT_DIR=<path>]
            \n\t- API_IP: IP address of the machine containing the Data Gathering Subsystem's API service.
            \n\t- POSTGRES_IP: IP address of the machine containing the PostgreSQL service.
            \n\t- EXTERNAL_POSTGRES_SERVER: indicates that the PostgreSQL server is externally provided,
                  and does not create a Docker container. Defaults to \"false\".
            \n\t- SKIP_DEPLOY: omits all deploy steps. Defaults to \"true\".
            \n\t- DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS: enables \"Expert Mode\", allowing to pass custom
                  args to the deploy script. Defaults to \"--all --with-tests\".
            \n\t- MACOS: if set, indicates that \"docker.for.mac.localhost\" should be used instead of the
                  local IP address.
            \n\t- ROOT_DIR: installs the Application under a custom directory. Defaults to
                  \"~/ClimateChangeApp\".
            \nIMPORTANT: DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS must be used in conjunction with SKIP_DEPLOY=false." 1;
fi


# Warnings
if  [ "$SKIP_DEPLOY" == "true" ]; then
    message -1 "[INFO] Deploy operations will be skipped for the Data Conversion Subsystem component.";
    DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--skip-all";
else
    message -1 "[INFO] Using default values for DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS.";
    DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
fi


# Overriding IP values if HOST_IP is present
if [ "$MACOS" == "true" ]; then
    if [ "$EXTERNAL_POSTGRES_SERVER" == "false" ]; then
        message -1 "[INFO] Since host OS is macOS/OS X, setting POSTGRES_IP to \"docker.for.mac.localhost\".";
        POSTGRES_IP="docker.for.mac.localhost";
    fi
    if [ "$API_IP" == $(calculate_ip_address) ]; then
        message -1 "[INFO] Since host OS is macOS/OS X and API_IP is the local machine's IP, setting API_IP to
                   \"docker.for.mac.localhost\".";
        API_IP="docker.for.mac.localhost";
    fi
fi
message -1 "[INFO] Deploying the Data Gathering Subsystem to the local machine. POSTGRES_IP has been set to \"$POSTGRES_IP\".";
message -1 "[INFO] API_IP has been set to \"$API_IP\".";
message 3 "Hint: If the value of POSTGRES_IP is incorrect, you can override it by invoking: \"./install.sh POSTGRES_IP=<IP>\".";
message 3 "Hint: If the value of API_IP is incorrect, you can override it by invoking: \"./install.sh API_IP=<IP>\".";

# Overriding default ROOT_DIR?
if [ "$ROOT_DIR" != "~/ClimateChangeApp" ]; then
    message -1 "[INFO] Deploying the application under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";

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
docker-compose build --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg API_IP=${API_IP} \
                     --build-arg DEPLOY_ARGS="${DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS}" data_conversion_subsystem;
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Conversion Subsystem image could not be built." 1;
fi


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
if [ "$EXTERNAL_POSTGRES_SERVER" == "true" ]; then
    message 2 "- PostgreSQL: external";
else
    message 2 "- PostgreSQL: up";
fi
message 2 "- Data Conversion Subsystem: built";
echo "";
