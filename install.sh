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
            \n • --cache-server-port xxxxx: sets the exposed Cache server port. Defaults to 11211.
            \n • --cache-server-size <size>: specifies the maximum size of the cache server (in MB). Defaults to 512 MB.
            \n • --hide-containers: makes Docker containers not reachable from the Internet.
            \n • --host-ip xxx.xxx.xxx.xxx: specifies the IP address of the machine. By default, this installer attempts
            \n\t  to resolve the machine's IP address. Invoke \"./install.sh --show-ip\" to display the resolved IP address.
            \n • --macos: sets \"docker.for.mac.host.internal\" as the local IP address (Docker issue).
            \n • --mongodb-port xxxxx: sets the exposed MongoDB port. Defaults to 27017.
            \n • --perform-deploy-actions: installs the application performing all deploy steps. By default, deploy
            \n\t   steps are skipped.
            \n • --postgres-port xxxxx: sets the exposed PostgreSQL port. Defaults to 5432.
            \n • --root-dir <path>: installs the Application under a custom directory. Defaults to \"~/ClimateChangeApp\".
            \n • --run-telegram: launches the Telegram Configurator service after building it.
            \n • --show-ip: displays the IP address of the machine. If multiple IP's, displays them all.
            \n • --superuser-name: Name of the web application's superuser, which will be able to login at \"/admin\"
            \n\t   in the web application.
            \n • --superuser-password: Password of the web application's superuser.
            \n • --uid <val>: sets the UID of the user executing the Subsystem. Using \"0\" or \"root\" is not recommended.
            \n\t   Defaults to the current user's UID." $1;
}


# ---------- Definitions ---------- #

# Setting default values
API_PORT=5000;
CACHE_SERVER_PORT=11211
CACHE_SERVER_SIZE=256
EXPOSE_CONTAINERS=true;
HOST_IP=$(get_ip_address);
MACOS=false;
MONGODB_PORT=27017;
POSTGRES_PORT=5432;
ROOT_DIR=~/ClimateChangeApp;
RUN_TELEGRAM=false;
SKIP_DEPLOY=true;
SUPERUSER_USERNAME=""
SUPERUSER_PASSWORD=""
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
                cache-server-port)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--cache-server-port" ${VAL};
                    CACHE_SERVER_PORT=${VAL};
                ;;
                cache-server-size)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--cache-server-size" ${VAL};
                    CACHE_SERVER_SIZE=${VAL};
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
                superuser-name)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty "--superuser-name" ${VAL}
                    SUPERUSER_USERNAME=${VAL};
                ;;
                superuser-password)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty "--superuser-password" ${VAL}
                    SUPERUSER_PASSWORD=${VAL};
                ;;
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
    message -1 "[INFO] Setting HOST_IP to \"docker.for.mac.host.internal\".";
    HOST_IP="docker.for.mac.host.internal";
fi
export HOST_IP=${HOST_IP};
message -1 "[INFO] Deploying all components to the local machine. HOST_IP has been set to \"$HOST_IP\".";
message 3 "Hint: If the value of HOST_IP is incorrect, you can override it by invoking: \"./install.sh --host-ip <IP>\".";


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
    WEB_APPLICATION_SUBSYSTEM_DEPLOY_ARGS="--skip-all";
    TELEGRAM_CONFIGURATOR_DEPLOY_ARGS="--skip-all";
    UTILITIES_DEPLOY_ARGS="--skip-all";
else
    message -1 "[INFO] Using default values for all DEPLOY_ARGS.";
    API_DEPLOY_ARGS="--all --with-tests";
    DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
    DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
    WEB_APPLICATION_SUBSYSTEM_DEPLOY_ARGS="--all --with-tests";
    TELEGRAM_CONFIGURATOR_DEPLOY_ARGS="--with-tests";
    UTILITIES_DEPLOY_ARGS="--with-tests";
fi
if [ "$MACOS" == "true" ] && [ "$EXPOSE_CONTAINERS" == "false" ]; then
    message 3 "[NOTE] --macos is no necessary when --hide-containers is passed as an argument. The installer is able to resolve the IP addresses via Docker."
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
message 4 "[COMPONENT] MongoDB";

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
message 4 "[COMPONENT] PostgreSQL";

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
message 4 "[COMPONENT] Telegram Configurator";

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
message 4 "[COMPONENT] Utilities";
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg POSTGRES_PORT=${POSTGRES_PORT} \
                     --build-arg DEPLOY_ARGS="${UTILITIES_DEPLOY_ARGS}" utilities;

if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The Utilities component could not be built." 1;
fi


# Data Gathering Subsystem component
message 4 "[COMPONENT] Data Gathering Subsystem";

# Building the Data Gathering Subsystem component
docker-compose build --build-arg MONGODB_IP=${MONGODB_IP} --build-arg MONGODB_PORT=${MONGODB_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_GATHERING_SUBSYSTEM_DEPLOY_ARGS}" \
                     --build-arg USER=${USER} data_gathering_subsystem;
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Gathering Subsystem image could not be built." 1;
fi


# API component
message 4 "[COMPONENT] API";

# Deleting the API service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=api)" ]; then
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
message 4 "[COMPONENT] Data Conversion Subsystem";

# Building the Data Conversion Subsystem component
docker-compose build --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg API_IP=${API_IP} \
                     --build-arg POSTGRES_PORT=${POSTGRES_PORT} --build-arg API_PORT=${API_PORT} \
                     --build-arg DEPLOY_ARGS="${DATA_CONVERSION_SUBSYSTEM_DEPLOY_ARGS}" \
                     --build-arg USER=${USER} data_conversion_subsystem;
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Conversion Subsystem image could not be built." 1;
fi


# Cache server component
message 4 "[COMPONENT] Cache server (Memcached)";

# Deleting the Cache server service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=cache_server)" ]; then
    message -1 "[INFO] Removing previous Cache server container.";
    docker stop cache_server;
    docker rm cache_server;
fi

# Launching the Cache server service
message -1 "[INFO] Launching the  Cache server service.";
docker-compose build cache_server;
docker-compose up -d cache_server;
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The  Cache server service could not be initialized." 1;
fi

# Getting internal IP address
CACHE_SERVER_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' cache_server)"
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] Could not retrieve the local  Cache server address." 1;
else
    message -1 "[INFO] Using \"$CACHE_SERVER_IP\" as the  Cache server address.";
fi


#  Web Application Subsystem component
message 4 "[COMPONENT] Web Application Subsystem";

# Building the Web Application Subsystem component
docker-compose build --build-arg CACHE_SERVER_IP=${CACHE_SERVER_IP} --build-arg CACHE_SERVER_PORT=${CACHE_SERVER_PORT} \
                     --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg POSTGRES_PORT=${POSTGRES_PORT} \
                     --build-arg SUPERUSER_USERNAME=${SUPERUSER_USERNAME} --build-arg SUPERUSER_PASSWORD=${SUPERUSER_PASSWORD} \
                     --build-arg DEPLOY_ARGS="${WEB_APPLICATION_SUBSYSTEM_DEPLOY_ARGS}" --build-arg USER=${USER} web_application_subsystem
if [ $? != 0 ]; then
    exit_with_message 1 "> The Web Application Subsystem image could not be built." 1;
fi

# Launching the Web Application Subsystem
docker-compose up -d web_application_subsystem


# Cache server component
message 4 "[COMPONENT] Proxy server (NginX)";

# Deleting the Cache server service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=proxy_server)" ]; then
    message -1 "[INFO] Removing previous Proxy server container.";
    docker stop proxy_server;
    docker rm proxy_server;
fi

# Launching the Proxy server
docker-compose build proxy_server
docker-compose up -d proxy_server


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
message 2 "\t• API: up";
message 2 "\t• Cache server: up";
message 2 "\t• Data Conversion Subsystem: built";
message 2 "\t• Data Gathering Subsystem: built";
message 2 "\t• MongoDB: up";
message 2 "\t• PostgreSQL: up";
message 2 "\t• Proxy Server: up";
message 2 "\t• Web Application Subsystem: up";
echo "";
