#! /bin/bash

# ---------- Functions ---------- #

source "./utilities/bash_util.sh"

# Displays script usage and exits.
# :param $1: Exit code.
function usage () {
    exit_with_message 1 "Installs the Data Gathering Subsystem's API component.
            \n\n> usage: install.sh [-h] [--help] [--version] [--api-port xxxxx] [--deploy-args \"<args>\"]
            \n\t[--external-mongodb-server] [--hide-containers] [--macos] [--mongodb-ip xxx.xxx.xxx.xxx]
            \n\t[--mongodb-port xxxxx] [--perform-deploy-actions] [--root-dir <path>] [--run] [--show-ip] [--uid <val>]
            \n • -h, --help: shows this message.
            \n • --version: displays app's version.
            \n • --api-port xxxxx: sets the exposed API port. Defaults to 5000.
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
            \n • --run: launches the API service after building it.
            \n • --show-ip: displays the IP address of the machine. If multiple IP's, displays them all.
            \n • --uid <val>: sets the UID of the user executing the Subsystem. Using \"0\" or \"root\" is not recommended.
            \n\t   Defaults to the current user's UID." $1;
}


# ---------- Definitions ---------- #

# Setting default values
DEPLOY_ARGS=null;
API_PORT=5000;
EXPOSE_CONTAINERS=true;
EXTERNAL_MONGODB_SERVER=false;
MACOS=false;
MONGODB_IP=$(get_ip_address);
MONGODB_PORT=27017;
ROOT_DIR=~/ClimateChangeApp;
RUN=false;
SKIP_DEPLOY=true;
USER=$(id -u)


# ---------- Argument manipulation ---------- #

# Parsing arguments
EXPECTED_INPUT=":h-:"
while getopts "$EXPECTED_INPUT" ARG; do
    case ${ARG} in
        h) usage 0 ;;
        -) case ${OPTARG} in
                help) usage 0 ;;
                version) show_app_version ;;
                api-port)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--api-port" ${VAL};
                    API_PORT=${VAL};
                ;;
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
                run) RUN=true ;;
                show-ip) show_ip_addresses ;;
                uid)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--uid" ${VAL};
                    ensure_positive_integer "--uid" ${VAL}
                    USER=${VAL};
                ;;
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
    message 3 "[WARNING] Parameter DEPLOY_ARGS has been set, but SKIP_DEPLOY is true. The value will be overridden
              to \"--skip-all\".";
elif [ "$SKIP_DEPLOY" == "true" ]; then
    message -1 "[INFO] Deploy operations will be skipped for the API component.";
    DEPLOY_ARGS="--skip-all"
elif [ "$DEPLOY_ARGS" == "null" ]; then
    message -1 "[INFO] Using default values for DEPLOY_ARGS.";
    DEPLOY_ARGS="--all --with-tests";
fi


# Displaying GID and UID info
if [ "$USER" == "0" ]; then
    message 3 "[WARNING] Running the Subsystem as the root is not recommended.";
else
    message -1 "[INFO] Setting Subsystem's UID: $USER."
fi


# Overriding IP values if HOST_IP is present
if ([ "$MACOS" == "true" ] && [ "$EXTERNAL_MONGODB_SERVER" == "false" ] ); then
    message -1 "[INFO] Since host OS is macOS/OS X, setting MONGODB_IP to \"docker.for.mac.localhost\".";
    MONGODB_IP="docker.for.mac.localhost";
fi
export HOST_IP=${MONGODB_IP}
message -1 "[INFO] Deploying the API component to the local machine. MONGODB_IP has been set to \"$MONGODB_IP\".";
message 3 "Hint: If the value of MONGODB_IP is incorrect, you can override it by invoking: \"./install.sh MONGODB_IP=<IP>\".";


# Binding containers to local?
if [ "$EXPOSE_CONTAINERS" == "true" ]; then
    message -1 "[INFO] Docker containers will be reachable from the Internet.";
    export BIND_IP_ADDRESS='0.0.0.0';
else
    export BIND_IP_ADDRESS='127.0.0.1'
    message 3 "[WARNING] Docker containers will not be reachable from the Internet. Binding connections to IP address: $BIND_IP_ADDRESS";
fi


# Overriding default ROOT_DIR?
if [ "$ROOT_DIR" != ~/ClimateChangeApp ]; then
    message -1 "[INFO] Deploying the API component under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";


# ---------- Installation ---------- #

# MongoDB component
message 4 "[COMPONENT] MongoDB";

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


# API component
message 4 "[COMPONENT] API";

# Deleting the API service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=api)" ]; then
    message -1 "[INFO] Removing previous API container.";
    docker stop api;
    docker rm api;
fi

# Building the API service
message -1 "[INFO] Building the API image."
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                 --build-arg API_PORT=${API_PORT} --build-arg DEPLOY_ARGS="${DEPLOY_ARGS}" --build-arg USER=${USER} api
if [ $? != 0 ]; then
    exit_with_message 1 "[INFO] The API image could not be built." 1;
fi

# Launching the API service
if [ "$RUN" == "true" ]; then
    message -1 "[INFO] Launching the API service.";
    docker-compose up -d api;
    if [ $? != 0 ]; then
        exit_with_message 1 "> The API service could not be initialized." 1;
    fi
fi


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
if [ "$EXTERNAL_MONGODB_SERVER" == "true" ]; then
    message 2 "\t• MongoDB: external";
else
    message 2 "\t• MongoDB: up";
fi
if [ "$RUN" == "true" ]; then
    message 2 "\t• API: up";
else
    message 2 "\t• API: built";
fi
echo "";
