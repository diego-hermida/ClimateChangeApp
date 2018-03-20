#! /bin/bash

# ---------- Functions ---------- #

source "./utilities/bash_util.sh"

# Displays script usage and exits.
# :param $1: Exit code.
function usage () {
    exit_with_message 1 "Installs the Data Gathering Subsystem component.
            \n\n> usage: install.sh [-h] [--help] [--version] [--deploy-args \"<args>\"] [--external-mongodb-server]
            \n\t[--hide-containers] [--macos] [--mongodb-ip xxx.xxx.xxx.xxx] [--mongodb-port xxxxx]
            \n\t[--perform-deploy-actions] [--root-dir <path>] [--show-ip]
            \n • -h, --help: shows this message.
            \n • --version: displays app's version.
            \n • --deploy-args \"<args>\": enables \"Expert Mode\", allowing to pass custom args to the deploy script.
            \n\t   Defaults to \"--all --with-tests\". Must be used in conjunction with --perform-deploy-actions.
            \n • --external-mongodb-server: indicates that the MongoDB server is externally provided, and does not
            \n\t   create a Docker container.
            \n • --hide-containers: makes Docker containers not reachable from the Internet.
            \n • --macos: sets \"docker.for.mac.localhost\" as the local IP address (Docker issue).
            \n • --mongodb-ip xxx.xxx.xxx.xxx: sets the IP address of the MongoDB server. Defaults to the machine's
            \n\t   IP address. Invoke \"./install.sh --show-ip\" to display the resolved IP address.
            \n • --mongodb-port xxxxx: sets the exposed MongoDB port. Defaults to 27017.
            \n • --perform-deploy-actions: installs the application performing all deploy steps. By default, deploy
            \n\t   steps are skipped.
            \n • --root-dir <path>: installs the Application under a custom directory. Defaults to \"~/ClimateChangeApp\".
            \n • --show-ip: displays the IP address of the machine. If multiple IP's, displays them all." $1;
}


# ---------- Definitions ---------- #

# Setting default values
DEPLOY_ARGS=null;
EXPOSE_CONTAINERS=true;
EXTERNAL_MONGODB_SERVER=false;
MACOS=false;
MONGODB_IP=$(get_ip_address);
MONGODB_PORT=27017;
ROOT_DIR="~/ClimateChangeApp";
SHOW_HELP=false;
SHOW_IP=false;
SKIP_DEPLOY=true;


# ---------- Argument manipulation ---------- #

# Parsing arguments
EXPECTED_INPUT=":h-:"
while getopts "$EXPECTED_INPUT" ARG; do
    case ${ARG} in
        h) usage 0 ;;
        -) case ${OPTARG} in
                help) usage 0 ;;
                version) show_app_version ;;
                deploy-args)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--deploy-args" ${VAL};
                    DEPLOY_ARGS=${VAL};
                ;;
                external-mongodb-server) EXTERNAL_MONGODB_SERVER=true ;;
                hide-containers) EXPOSE_CONTAINERS=false ;;
                macos) MACOS=true ;;
                mongodb-ip)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--mongodb-ip" ${VAL};
                    MONGODB_IP=${VAL};
                ;;
                mongodb-port)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--mongodb-port" ${VAL};
                    MONGODB_PORT=${VAL};
                ;;
                perform-deploy-actions) SKIP_DEPLOY=false ;;
                root-dir)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--root-dir" ${VAL};
                    ROOT_DIR=${VAL};
                ;;
                show-ip) show_ip_addresses ;;
                :) exit_with_message 1 "Illegal option: \"--$OPTARG\" requires an argument" >&2 ;;
                *) exit_with_message 1 "Unrecognized option: --$OPTARG" >&2 ;;
            esac
        ;;
        :) exit_with_message 1 "Illegal option: \"-$OPTARG\" requires an argument" >&2 ;;
        *) exit_with_message 1 "Unrecognized option: -$OPTARG" >&2 ;;
    esac
done


# Warnings
if [ "$DEPLOY_ARGS" != "null" ] && [ "$SKIP_DEPLOY" == "true" ]; then
    message 3 "[WARNING] Parameter DEPLOY_ARGS has been set, but SKIP_DEPLOY is true. 
              The value will be overridden to \"--skip-all\".";
elif [ "$SKIP_DEPLOY" == "true" ]; then
    message -1 "[INFO] Deploy operations will be skipped for the Data Gathering Subsystem component.";
    DEPLOY_ARGS="--skip-all"
elif [ "$DEPLOY_ARGS" == "null" ]; then
    message -1 "[INFO] Using default values for DEPLOY_ARGS.";
    DEPLOY_ARGS="--all --with-tests";
fi


# Overriding IP values if HOST_IP is present
if ([ "$MACOS" == "true" ] && [ "$EXTERNAL_MONGODB_SERVER" == "false" ] ); then
    message -1 "[INFO] Since host OS is macOS/OS X, setting MONGODB_IP to \"docker.for.mac.localhost\".";
    MONGODB_IP="docker.for.mac.localhost";
fi
export HOST_IP=${MONGODB_IP}
message -1 "[INFO] Deploying the Data Gathering Subsystem component to the local machine. MONGODB_IP has been set to \"$MONGODB_IP\".";
message 3 "Hint: If the value of MONGODB_IP is incorrect, you can override it by invoking: \"./install.sh MONGODB_IP=<IP>\".";


# Binding containers to local?
if [ "$EXPOSE_CONTAINERS" == "true" ]; then
    message -1 "[INFO] Docker containers will be reachable from the Internet.";
    export BIND_IP_ADDRESS='0.0.0.0';
else
    if [ "$MACOS" == "true" ]; then
        export BIND_IP_ADDRESS='127.0.0.1'
    else
        export BIND_IP_ADDRESS=${HOST_IP}
    fi
    message 3 "[WARNING] Docker containers will not be reachable from the Internet. Binding connections to IP address: $HOST_IP";
fi


# Overriding default ROOT_DIR?
if [ "$ROOT_DIR" != "~/ClimateChangeApp" ]; then
    message -1 "[INFO] Deploying the Data Gathering Subsystem component under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";


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
                     --build-arg DEPLOY_ARGS="${DEPLOY_ARGS}" data_gathering_subsystem
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Gathering Subsystem image could not be built." 1;
fi


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
if [ "$EXTERNAL_MONGODB_SERVER" == "true" ]; then
    message 2 "\t• MongoDB: external";
    else message 2 "\t• MongoDB: up";
fi
message 2 "\t• Data Gathering Subsystem: built";
echo "";
