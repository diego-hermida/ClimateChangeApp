#! /bin/bash

# ---------- Functions ---------- #

source "./utilities/bash_util.sh"

# Displays script usage and exits.
# :param $1: Exit code.
function usage () {
    exit_with_message 1 "Installs the application components.
            \n\n> usage: install.sh [-h] [--help] [--version] [--api-port xxxxx] [--hide-containers] [--host-ip xxx.xxx.xxx.xxx]
            \n\t[--macos] [--mongodb-port xxxxx] [--perform-deploy-actions] [--postgres-port xxxxx] [--root-dir <path>]
            \n\t[--run-telegram] [--show-ip]
            \n • -h, --help: shows this message.
            \n • --version: displays app's version.
            \n • --api-port xxxxx: sets the exposed API port. Defaults to 5000.
            \n • --hide-containers: makes Docker containers not reachable from the Internet.
            \n • --host-ip xxx.xxx.xxx.xxx: specifies the IP address of the machine. By default, this installer attempts
            \n\t  to resolve the machine's IP address. Invoke \"./install.sh --show-ip\" to display the resolved IP address.
            \n • --macos: sets \"docker.for.mac.localhost\" as the local IP address (Docker issue).
            \n • --mongodb-port xxxxx: sets the exposed MongoDB port. Defaults to 27017.
            \n • --perform-deploy-actions: installs the application performing all deploy steps. By default, deploy
            \n\t   steps are skipped.
            \n • --postgres-port xxxxx: sets the exposed PostgreSQL port. Defaults to 5432.
            \n • --root-dir <path>: installs the Application under a custom directory. Defaults to \"~/ClimateChangeApp\".
            \n • --run-telegram: launches the Telegram Configurator service after building it.
            \n • --show-ip: displays the IP address of the machine. If multiple IP's, displays them all.
            \n • --uid <val>: sets the UID of the user executing the Subsystem. Using \"0\" or \"root\" is not recommended.
            \n\t   Defaults to the current user's UID." $1;
}


# ---------- Definitions ---------- #

# Setting default values
API_PORT=5000;
EXPOSE_CONTAINERS=true;
HOST_IP=$(get_ip_address);
MACOS=false;
MONGODB_PORT=27017;
POSTGRES_PORT=5432;
ROOT_DIR=~/ClimateChangeApp;
RUN_TELEGRAM=false;
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
                hide-containers) EXPOSE_CONTAINERS=false ;;
                host-ip)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--host-ip" ${VAL};
                    HOST_IP=${VAL};
                ;;
                macos) MACOS=true ;;
                mongodb-port)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--mongodb-port" ${VAL};
                    MONGODB_PORT=${VAL};
                ;;
                perform-deploy-actions) SKIP_DEPLOY=false ;;
                postgres-port)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--postgres-port" ${VAL};
                    POSTGRES_PORT=${VAL};
                ;;
                root-dir)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--root-dir" ${VAL};
                    ROOT_DIR=${VAL};
                ;;
                run-telegram) RUN_TELEGRAM=true ;;
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


# Displaying GID and UID info
if [ "$USER" == "0" ]; then
    message 3 "[WARNING] Running the Subsystem as the root is not recommended.";
else
    message -1 "[INFO] Setting Subsystem's UID: $USER."
fi


# Overriding IP values if HOST_IP is present
if [ "$MACOS" == "true" ]; then
    message -1 "[INFO] Setting HOST_IP to \"docker.for.mac.localhost\".";
    HOST_IP="docker.for.mac.localhost";
fi
export HOST_IP=${HOST_IP};
message -1 "[INFO] Deploying all components to the local machine. HOST_IP has been set to \"$HOST_IP\".";
message 3 "Hint: If the value of HOST_IP is incorrect, you can override it by invoking: \"./install.sh HOST_IP=<IP>\".";


# Binding containers to local?
if [ "$EXPOSE_CONTAINERS" == "true" ]; then
    message -1 "[INFO] Docker containers will be reachable from the Internet.";
    export BIND_IP_ADDRESS='0.0.0.0';
else
    export BIND_IP_ADDRESS='127.0.0.1'
    message 3 "[WARNING] Docker containers will not be reachable from the Internet. Binding connections to IP address: $BIND_IP_ADDRESS";
fi


# Warnings
if  [ "$SKIP_DEPLOY" == "true" ]; then
    message -1 "[INFO] Deploy operations will be skipped for all components."
    API_DEPLOY_ARGS="--skip-all";
    DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--skip-all";
    DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--skip-all";
    TELEGRAM_CONFIGURATOR_DEPLOY_ARGS="--skip-all";
    UTILITIES_DEPLOY_ARGS="--skip-all";
else
    message -1 "[INFO] Using default values for all DEPLOY_ARGS.";
    API_DEPLOY_ARGS="--all --with-tests";
    DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
    DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
    TELEGRAM_CONFIGURATOR_DEPLOY_ARGS="--with-tests";
    UTILITIES_DEPLOY_ARGS="--with-tests";
fi


# Overriding default ROOT_DIR?
if [ "$ROOT_DIR" != ~/ClimateChangeApp ]; then
    message -1 "[INFO] Deploying the application under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";


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
    exit_with_message 1 "[ERROR] The MongoDB service could not be initialized." 1;
fi

# Getting internal IP address, if --hide-containers.
if [ "$EXPOSE_CONTAINERS" == "true" ]; then
    MONGODB_IP=${HOST_IP};
else
    MONGODB_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' mongodb)"
    if [ $? != 0 ]; then
        exit_with_message 1 "[ERROR] Could not retrieve the local MongoDB IP address." 1;
    else
        message -1 "[INFO] Using \"$MONGODB_IP\" as the MongoDB IP address.";
    fi
fi


# PostgreSQL component
message 4 "[COMPONENT] Building and launching the PostgreSQL service.";

# Deleting the PostgreSQL service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=postgres)" ]; then
    message -1 "[INFO] Removing previous PostgreSQL container.";
    docker stop postgres;
    docker rm postgres;
fi

# Launching the PostgreSQL service
message -1 "[INFO] Launching the PostgreSQL service.";
docker-compose up -d postgres;
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The PostgreSQL service could not be initialized." 1;
fi

# Getting internal IP address, if --hide-containers.
if [ "$EXPOSE_CONTAINERS" == "true" ]; then
    POSTGRES_IP=${HOST_IP};
else
    POSTGRES_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgres)"
    if [ $? != 0 ]; then
        exit_with_message 1 "[ERROR] Could not retrieve the local PostgreSQL IP address." 1;
    else
        message -1 "[INFO] Using \"$POSTGRES_IP\" as the PostgeSQL IP address.";
    fi
fi


# Telegram Configurator component
message 4 "[COMPONENT] Building the Telegram Configurator component.";

# Building the Telegram Configurator component
docker-compose build --build-arg DEPLOY_ARGS="${TELEGRAM_CONFIGURATOR_DEPLOY_ARGS}" telegram_bot;
if [ $? != 0 ]; then
    exit_with_message 1 "> The Telegram Configurator image could not be built." 1;
fi
# Running the Telegram Configurator component
if [ "$RUN_TELEGRAM" == "true" ]; then
    message -1 "[INFO] Running the Telegram Configurator component.";
    echo "";
    docker run --rm -i -t --name telegram_bot diegohermida/telegram_bot:latest;

    # Displaying installation summary
    if [ $? != 0 ]; then
        exit_with_message 1 "\n[ERROR] The Telegram Configurator did not exit normally. You should rerun this installer." 1;
    else
        message 2 "\n[SUCCESS] The Telegram Configurator was successful.";
        exit_with_message -1 "[INFO] The installation will finish now. Be sure to follow the Telegrama Configurator
                    instructions, and restart this installer without RUN_TELEGRAM=true." 0
    fi
fi


# Utilities component
message 4 "[COMPONENT] Building and testing the Utilities component.";
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg POSTGRES_PORT=${POSTGRES_PORT} \
                     --build-arg DEPLOY_ARGS="${UTILITIES_DEPLOY_ARGS}" utilities;

if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The Utilities component could not be built." 1;
fi


# Data Gathering Subsystem component
message 4 "[COMPONENT] Building the Data Gathering Subsystem.";

# Building the Data Gathering Subsystem component
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS}" \
                     --build-arg USER=${USER} data_gathering_subsystem;
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Gathering Subsystem image could not be built." 1;
fi


# API component
message 4 "[COMPONENT] Building and launching the API service.";

# Deleting the API service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=api_ci)" ]; then
    message -1 "[INFO] Removing previous API container.";
    docker stop api_ci;
    docker rm api_ci;
fi

# Building the API service
message -1 "[INFO] Building the API image."
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg DEPLOY_ARGS="${API_DEPLOY_ARGS}" --build-arg USER=${USER} api;
if [ $? != 0 ]; then
    exit_with_message 1 "[INFO] The API image could not be built." 1;
fi

# Launching the API service
message -1 "[INFO] Launching the API service.";
docker-compose up -d api;
if [ $? != 0 ]; then
    exit_with_message 1 "> The API service could not be initialized." 1;
fi

# Getting internal IP address, if --hide-containers.
if [ "$EXPOSE_CONTAINERS" == "true" ]; then
    API_IP=${HOST_IP};
else
    API_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' api)"
    if [ $? != 0 ]; then
        exit_with_message 1 "[ERROR] Could not retrieve the local API IP address." 1;
    else
        message -1 "[INFO] Using \"$API_IP\" as the API IP address.";
    fi
fi


# Data Conversion Subsystem component
message 4 "[COMPONENT] Building the Data Conversion Subsystem.";

# Building the Data Conversion Subsystem component
docker-compose build --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg API_IP=${API_IP} \
                     --build-arg POSTGRES_PORT=${POSTGRES_PORT} --build-arg API_PORT=${API_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS}" \
                     --build-arg USER=${USER} data_conversion_subsystem;
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Conversion Subsystem image could not be built." 1;
fi


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
message 2 "\t• API: up";
message 2 "\t• Data Conversion Subsystem: built";
message 2 "\t• Data Gathering Subsystem: built";
message 2 "\t• MongoDB: up";
message 2 "\t• PostgreSQL: up";
echo "";
