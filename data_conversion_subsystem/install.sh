#! /bin/bash

# ---------- Functions ---------- #

source "./utilities/bash_util.sh"

# Displays script usage and exits.
# :param $1: Exit code.
function usage () {
    exit_with_message 1 "Installs the Data Conversion Subsystem component.
            \n\n> usage: install.sh [-h] [--help] [--version] [--api-ip xxx.xxx.xxx.xxx] [--api-port xxxxx]
            \n\t[--deploy-args \"<args>\"] [--external-postgres-server] [--hide-containers] [--macos]
            \n\t[--postgres-ip xxx.xxx.xxx.xxx] [--postgres-port xxxxx] [--perform-deploy-actions] [--root-dir <path>]
            \n\t[--show-ip]
            \n • -h, --help: shows this message.
            \n • --version: displays app's version.
            \n • --api-ip xxx.xxx.xxx.xxx: specifies the IP address of the API server. Defaults to the machine's
            \n\t   IP address. Invoke \"./install.sh --show-ip\" to display the resolved IP address.
            \n • --api-port xxxxx: sets the exposed API port. Defaults to 5000.
            \n • --deploy-args \"<args>\": enables \"Expert Mode\", allowing to pass custom args to the deploy script.
            \n\t   Defaults to \"--all --with-tests\". Must be used in conjunction with --perform-deploy-actions.
            \n • --external-postgres-server: indicates that the PostgreSQL server is externally provided, and does not
            \n\t   create a Docker container.
            \n • --hide-containers: makes Docker containers not reachable from the Internet.
            \n • --macos: sets \"docker.for.mac.localhost\" as the local IP address (Docker issue).
            \n • --postgres-ip xxx.xxx.xxx.xxx: sets the IP address of the PostgreSQL server. Defaults to the machine's
            \n\t   IP address. Invoke \"./install.sh --show-ip\" to display the resolved IP address.
            \n • --postgres-port xxxxx: sets the exposed PostgreSQL port. Defaults to 5432.
            \n • --perform-deploy-actions: installs the application performing all deploy steps. By default, deploy
            \n\t   steps are skipped.
            \n • --root-dir <path>: installs the Application under a custom directory. Defaults to \"~/ClimateChangeApp\".
            \n • --show-ip: displays the IP address of the machine. If multiple IP's, displays them all." $1;
}


# ---------- Definitions ---------- #

# Setting default values
API_IP=$(get_ip_address);
API_PORT=5000;
DEPLOY_ARGS=null;
EXPOSE_CONTAINERS=true;
EXTERNAL_POSTGRES_SERVER=false;
MACOS=false;
POSTGRES_IP=$(get_ip_address);
POSTGRES_PORT=5432;
ROOT_DIR="~/ClimateChangeApp";
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
                api-ip)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--api-ip" ${VAL};
                    API_IP=${VAL};
                ;;
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
                external-postgres-server) EXTERNAL_POSTGRES_SERVER=true ;;
                hide-containers) EXPOSE_CONTAINERS=false ;;
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
    message -1 "[INFO] Deploy operations will be skipped for the Data Conversion Subsystem component.";
    DEPLOY_ARGS="--skip-all"
elif [ "$DEPLOY_ARGS" == "null" ]; then
    message -1 "[INFO] Using default values for DEPLOY_ARGS.";
    DEPLOY_ARGS="--all --with-tests";
fi


# Overriding IP values if HOST_IP is present
if ([ "$MACOS" == "true" ] && [ "$EXTERNAL_POSTGRES_SERVER" == "false" ] ); then
    message -1 "[INFO] Since host OS is macOS/OS X, setting POSTGRES_IP to \"docker.for.mac.localhost\".";
    POSTGRES_IP="docker.for.mac.localhost";
fi
export HOST_IP=${POSTGRES_IP}
message -1 "[INFO] Deploying the Data Conversion Subsystem component to the local machine. POSTGRES_IP has been set to \"$POSTGRES_IP\".";
message 3 "Hint: If the value of POSTGRES_IP is incorrect, you can override it by invoking: \"./install.sh POSTGRES_IP=<IP>\".";


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
    message -1 "[INFO] Deploying the Data Conversion Subsystem component under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";


# ---------- Installation ---------- #

# PostgreSQL component
message 4 "[COMPONENT] Building and launching the PostgreSQL service.";

if [ "$EXTERNAL_POSTGRES_SERVER" == "false" ]; then
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
else
    message -1 "[INFO] PostgreSQL server has been tagged as \"external\". Thus, the PostgreSQL Docker service won't be launched.";
fi


# Data Conversion Subsystem component
message 4 "[COMPONENT] Building the Data Conversion Subsystem.";

# Building the Data Conversion Subsystem component
docker-compose build --build-arg API_IP=${API_IP} --build-arg API_PORT=${API_PORT} \
                     --build-arg POSTGRES_IP=${POSTGRES_IP} --build-arg POSTGRES_PORT=${POSTGRES_PORT} \
                     --build-arg DEPLOY_ARGS="${DEPLOY_ARGS}" data_conversion_subsystem
if [ $? != 0 ]; then
    exit_with_message 1 "> The Data Conversion Subsystem image could not be built." 1;
fi


# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
if [ "$EXTERNAL_POSTGRES_SERVER" == "true" ]; then
    message 2 "\t• PostgreSQL: external";
    else message 2 "\t• PostgreSQL: up";
fi
message 2 "\t• Data Conversion Subsystem: built";
echo "";
