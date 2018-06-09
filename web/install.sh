#! /bin/bash

# ---------- Functions ---------- #

source "./utilities/bash_util.sh"

# Displays script usage and exits.
# :param $1: Exit code.
function usage () {
    exit_with_message 1 "Installs the Web Application Subsystem component.
            \n\n> usage: install.sh [-h] [--help] [--version] [--cache-server-port xxxxx] [--cache-server-size <size>]
            \n\t[--deploy-args \"<args>\"] [--macos] [--postgres-ip xxx.xxx.xxx.xxx] [--postgres-port xxxxx]
            \n\t[--perform-deploy-actions] [--root-dir <path>] [--show-ip] [--superuser-name <name>]
            \n\t[--superuser-password] [--uid <val>]
            \n • -h, --help: shows this message.
            \n • --version: displays app's version.
            \n • --cache-server-port xxxxx: sets the exposed Cache server port. Defaults to 11211.
            \n • --cache-server-size <size>: specifies the maximum size of the cache server (in MB). Defaults to 512 MB.
            \n • --deploy-args \"<args>\": enables \"Expert Mode\", allowing to pass custom args to the deploy script.
            \n\t   Defaults to \"--all --with-tests\". Must be used in conjunction with --perform-deploy-actions.
            \n • --macos: sets \"docker.for.mac.host.internal\" as the local IP address (Docker issue).
            \n • --postgres-ip xxx.xxx.xxx.xxx: sets the IP address of the PostgreSQL server. Defaults to the machine's
            \n\t   IP address. Invoke \"./install.sh --show-ip\" to display the resolved IP address.
            \n • --postgres-port xxxxx: sets the exposed PostgreSQL port. Defaults to 5432.
            \n • --perform-deploy-actions: installs the application performing all deploy steps. By default, deploy
            \n\t   steps are skipped.
            \n • --root-dir <path>: installs the Application under a custom directory. Defaults to \"~/ClimateChangeApp\".
            \n • --show-ip: displays the IP address of the machine. If multiple IP's, displays them all.
            \n • --superuser-name: Name of the web application's superuser, which will be able to login at \"/admin\"
            \n\t   in the web application.
            \n • --superuser-password: Password of the web application's superuser.
            \n • --uid <val>: sets the UID of the user executing the Subsystem. Using \"0\" or \"root\" is not recommended.
            \n\t   Defaults to the current user's UID." $1;
}


# ---------- Definitions ---------- #

# Setting default values
CACHE_SERVER_PORT=11211
CACHE_SERVER_SIZE=256
DEPLOY_ARGS=null;
EXPOSE_CONTAINERS=false;
MACOS=false;
POSTGRES_IP=$(get_ip_address);
POSTGRES_PORT=5432;
ROOT_DIR=~/ClimateChangeApp;
SKIP_DEPLOY=true;
SUPERUSER_USERNAME=""
SUPERUSER_PASSWORD=""
USER=$(id -u);


# ---------- Argument manipulation ---------- #

# Parsing arguments
EXPECTED_INPUT=":h-:"
while getopts "$EXPECTED_INPUT" ARG; do
    case ${ARG} in
        h) usage 0 ;;
        -) case ${OPTARG} in
                help) usage 0 ;;
                version) show_app_version ;;
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
                deploy-args)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--deploy-args" ${VAL};
                    DEPLOY_ARGS=${VAL};
                ;;
                macos) MACOS=true ;;
                postgres-ip)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--postgres-ip" ${VAL};
                    POSTGRES_IP=${VAL};
                ;;
                postgres-port)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--postgres-port" ${VAL};
                    POSTGRES_PORT=${VAL};
                ;;
                perform-deploy-actions) SKIP_DEPLOY=false ;;
                root-dir)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--root-dir" ${VAL};
                    ROOT_DIR=${VAL};
                ;;
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


# Warnings
if [ "$DEPLOY_ARGS" != "null" ] && [ "$SKIP_DEPLOY" == "true" ]; then
    message 3 "[WARNING] Parameter DEPLOY_ARGS has been set, but SKIP_DEPLOY is true.
              The value will be overridden to \"--skip-all\".";
elif [ "$SKIP_DEPLOY" == "true" ]; then
    message -1 "[INFO] Deploy operations will be skipped for the Web Application Subsystem component.";
    DEPLOY_ARGS="--skip-all"
elif [ "$DEPLOY_ARGS" == "null" ]; then
    message -1 "[INFO] Using default values for DEPLOY_ARGS.";
    DEPLOY_ARGS="--all --with-tests";
fi
if [ "$MACOS" == "true" ] && [ "$EXPOSE_CONTAINERS" == "false" ]; then
    message 3 "[NOTE] --macos is no necessary when --hide-containers is passed as an argument. The installer is able to resolve the IP addresses via Docker."
fi

# Displaying GID and UID info
if [ "$USER" == "0" ]; then
    message 3 "[WARNING] Running the Subsystem as the root is not recommended.";
else
    message -1 "[INFO] Setting Subsystem's UID: $USER."
fi


# Binding containers to local?
export BIND_IP_ADDRESS='127.0.0.1'
message 3 "[WARNING] Docker containers will not be reachable from the Internet (this does not affect
           to the web application). Binding connections to IP address: $BIND_IP_ADDRESS";



# Overriding default ROOT_DIR?
if [ "$ROOT_DIR" != ~/ClimateChangeApp ]; then
    message -1 "[INFO] Deploying the Web Application Subsystem component under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";


# ---------- Installation ---------- #

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


if [ "$POSTGRES_IP" == $(get_ip_address) ]; then
    POSTGRES_INTERNAL_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgres)"
    if [ $? != 0 ]; then
        if [ "$EXPOSE_CONTAINERS" == "false" ]; then
            exit_with_message 1 "[ERROR] Could not retrieve the local PostgreSQL IP address. The PostgreSQL component must be up in order to build this component." 1;
        else
            message 3 "[WARNING] Could not resolve the local API IP address. Using \"$POSTGRES_IP\" as the PostgreSQL IP address."
        fi
    else
        POSTGRES_IP=${POSTGRES_INTERNAL_IP}
        message -1 "[INFO] Using \"$POSTGRES_IP\" as the PostgreSQL IP address.";
    fi
fi


# Building the Web Application Subsystem component
docker-compose build --build-arg CACHE_SERVER_IP=${CACHE_SERVER_IP} --build-arg CACHE_SERVER_PORT=${CACHE_SERVER_PORT} \
                     --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg POSTGRES_PORT=${POSTGRES_PORT} \
                     --build-arg SUPERUSER_USERNAME=${SUPERUSER_USERNAME} --build-arg SUPERUSER_PASSWORD=${SUPERUSER_PASSWORD} \
                     --build-arg DEPLOY_ARGS="${DEPLOY_ARGS}" --build-arg USER=${USER} web_application_subsystem
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
message 2 "\t• Cache server: up";
message 2 "\t• PostgreSQL: external";
message 2 "\t• Proxy Server: up";
message 2 "\t• Web Application Subsystem: up";
echo "";
