#! /bin/bash

# ---------- Definitions ---------- #

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

# ---------- Functions ---------- #
# Setting default values
MONGODB_IP=$(calculate_ip_address);
EXTERNAL_MONGODB_SERVER=false;
SKIP_DEPLOY=true;
DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS=null;
MACOS=false;
ROOT_DIR="~/ClimateChangeApp";


# ---------- Argument manipulation ---------- #

# Parsing arguments
for ARGUMENT in "$@"
do
    KEY=$(echo $ARGUMENT | cut -f1 -d=)
    VALUE=$(echo $ARGUMENT | cut -f2 -d=)
    case "$KEY" in
            MONGODB_IP)                             MONGODB_IP=${VALUE} ;;
            SKIP_DEPLOY)                            SKIP_DEPLOY=${VALUE} ;;
            DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS)   DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS=${VALUE} ;;
            EXTERNAL_MONGODB_SERVER)                EXTERNAL_MONGODB_SERVER=${VALUE} ;;
            MACOS)                                  MACOS=${VALUE} ;;
            ROOT_DIR)                               ROOT_DIR=${VALUE} ;;
            *)
    esac
done

# Setting variables to lower case
SKIP_DEPLOY=echo "$SKIP_DEPLOY" | tr '[:upper:]' '[:lower:]';
DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS=echo "$DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS" | tr '[:upper:]' '[:lower:]';
EXTERNAL_MONGODB_SERVER=echo "$EXTERNAL_MONGODB_SERVER" | tr '[:upper:]' '[:lower:]';

# Ensuring variables contain legit values
if [ "$MONGODB_IP" == "null" ] || ([ "$SKIP_DEPLOY" != "true" ] && [ "$SKIP_DEPLOY" != "false" ]) ||
            ([ "$EXTERNAL_MONGODB_SERVER" != "true" ] && [ "$EXTERNAL_MONGODB_SERVER" != "false" ]); then
     exit_with_message 1 "> usage: install.sh MONGODB_IP=xxx.xxx.xxx.xxx [EXTERNAL_MONGODB_SERVER=true] [SKIP_DEPLOY=false]
            [DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS=<args>] [MACOS={true|false}] [ROOT_DIR=<path>]
            \n\t- MONGODB_IP: IP address of the machine containing the MongoDB service.
            \n\t- EXTERNAL_MONGODB_SERVER: indicates that the MongoDB server is externally provided,
                  and does not create a Docker container. Defaults to \"false\".
            \n\t- SKIP_DEPLOY: omits all deploy steps. Defaults to \"true\".
            \n\t- DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS: enables \"Expert Mode\", allowing to pass custom
                  args to the deploy script. Defaults to \"--all --with-tests\".
            \n\t- MACOS: if set, indicates that \"docker.for.mac.localhost\" should be used instead of the
                  local IP address.
            \n\t- ROOT_DIR: installs the Application under a custom directory. Defaults to
                  \"~/ClimateChangeApp\".
            \nIMPORTANT: DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS must be used in conjunction with SKIP_DEPLOY=false." 1;
fi


# Warnings
if [ "$DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS" != "null" ] && [ "$SKIP_DEPLOY" == "true" ]; then
    message 3 "[WARNING] Parameter DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS has been set, but SKIP_DEPLOY is true.
              The value will be overridden to \"--skip-all\".";
    elif [ "$SKIP_DEPLOY" == "true" ]; then
        message -1 "[INFO] Deploy operations will be skipped for the Data Gathering Subsystem component.";
        DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--skip-all"
    elif [ "$DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS" == "null" ]; then
        message -1 "[INFO] Using default values for DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS.";
        DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
fi


# Overriding IP values if HOST_IP is present
if ([ "$MACOS" == "true" ] && [ "$EXTERNAL_MONGODB_SERVER" == "false" ] ); then
    message -1 "[INFO] Since host OS is macOS/OS X, setting MONGODB_IP to \"docker.for.mac.localhost\".";
    MONGODB_IP="docker.for.mac.localhost";
fi
message -1 "[INFO] Deploying the Data Gathering Subsystem to the local machine. MONGODB_IP has been set to \"$MONGODB_IP\".";
message 3 "Hint: If the value of MONGODB_IP is incorrect, you can override it by invoking: \"./install.sh MONGODB_IP=<IP>\".";


# Overriding default ROOT_DIR?
if [ "$ROOT_DIR" != "~/ClimateChangeApp" ]; then
    message -1 "[INFO] Deploying the application under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";


# Setting port address
message -1 "[INFO] Using default value for MONGODB_PORT."
MONGODB_PORT=27017;

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
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS}" data_gathering_subsystem
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Gathering Subsystem image could not be built." 1;
fi


# Displaying installation summary
echo "";
if [ "$EXTERNAL_MONGODB_SERVER" == "true" ]; then
    message 2 "- MongoDB: external";
    else message 2 "- MongoDB: up";
fi
message 2 "- Data Gathering Subsystem: built";
echo "";
