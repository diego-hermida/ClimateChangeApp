#! /bin/bash

# ---------- Functions ---------- #

source "./utilities/bash_util.sh"

# Displays script usage and exits.
# :param $1: Exit code.
function usage () {
    exit_with_message 1 "Installs the Jenkins and SonarQube services for Continuous Integration and Continuous Inspection.
            \nA PostgreSQL instance will also be installed, in order to persist Sonar analysis and configuration data.
            \n\n> Security note: Jenkins and SonarQube containers will be reachable from the Internet. However, the
            \nSonarQube database will be bounded to a local network (unreachable from the Internet).
            \n\n> usage: install.sh [-h] [--help] [--version] [--force-build] [--host-ip xxx.xxx.xxx.xxx] [--jenkins-port xxxxx]
            \n\t[--jenkins-agents-port xxxxx] [--root-dir <path>] [--sonar-port xxxxx]
            \n • -h, --help: shows this message.
            \n • --version: displays app's version.
            \n • --force-build: builds the CI images even if they already exist.
            \n • --host-ip xxx.xxx.xxx.xxx: specifies the IP address of the machine. By default, this installer attempts
            \n\t  to resolve the machine's IP address. Invoke \"./install.sh --show-ip\" to display the resolved IP address.
            \n • --jenkins-port xxxxx: sets the exposed Jenkins port. Defaults to 8090.
            \n • --jenkins-agents-port xxxxx: sets the exposed Jenkins agents' port. Defaults to 50000.
            \n • --root-dir <path>: installs the CI components under a custom directory. Defaults to \"~/ClimateChangeApp\".
            \n • --sonar-port xxxxx: sets the exposed SonarQube port. Defaults to 9000." $1;
}


# ---------- Definitions ---------- #

FORCE_BUILD=false;
HOST_IP=$(get_ip_address);
JENKINS_PORT=8090;
JENKINS_AGENTS_PORT=50000;
ROOT_DIR=~/ClimateChangeApp;
SONAR_PORT=9000;


# ---------- Argument manipulation ---------- #

# Parsing arguments
EXPECTED_INPUT=":h-:"
while getopts "$EXPECTED_INPUT" ARG; do
    case "${ARG}" in
        h) usage 0 ;;
        -) case ${OPTARG} in
                help) usage 0 ;;
                version) show_app_version ;;
                force-build) FORCE_BUILD=true ;;
                host-ip)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--host-ip" ${VAL};
                    HOST_IP=${VAL};
                ;;
                jenkins-port)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--jenkins-port" ${VAL};
                    JENKINS_PORT=${VAL};
                ;;
                jenkins-agents-port)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--jenkins-agents-port" ${VAL};
                    JENKINS_AGENTS_PORT=${VAL};
                ;;
                root-dir)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--root-dir" ${VAL};
                    ROOT_DIR=${VAL};
                ;;
                sonar-port)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--sonar-port" ${VAL};
                    SONAR_PORT=${VAL};
                ;;
                :) exit_with_message 1 "Illegal option: \"--$OPTARG\" requires an argument" >&2 ;;
                *) exit_with_message 1 "Unrecognized option: --$OPTARG" >&2 ;;
            esac
        ;;
        :) exit_with_message 1 "Illegal option: \"-$OPTARG\" requires an argument" >&2 ;;
        *) exit_with_message 1 "Unrecognized option: -$OPTARG" >&2 ;;
    esac
done


# Overriding default ROOT_DIR?
if [ "$ROOT_DIR" != ~/ClimateChangeApp ]; then
    message -1 "[INFO] Deploying Jenkins and Sonar servers under custom directory: $ROOT_DIR.";
else
    message -1 "[INFO] Using default directory for deployment: $ROOT_DIR.";
fi
export ROOT_DIR="$ROOT_DIR";


# Setting ports
export JENKINS_PORT=${JENKINS_PORT}
export JENKINS_AGENTS_PORT=${JENKINS_AGENTS_PORT}
export SONAR_PORT=${SONAR_PORT}


# ---------- Installation ---------- #

# Jenkins component
message 4 "[COMPONENT] Jenkins";

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
    docker-compose build --build-arg HOST_IP=${HOST_IP} --build-arg JENKINS_PORT=${JENKINS_PORT} \
                         --build-arg JENKINS_AGENTS_PORT=${JENKINS_AGENTS_PORT} jenkins;
    if [ $? != 0 ]; then
        exit_with_message 1 "[ERROR] The Jenkins image could not be built." 1;
    fi
fi
docker-compose up -d jenkins;
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The Jenkins service could not be initialized." 1;
fi


# PostgreSQL component
message 4 "[COMPONENT] SonarQube PostgeSQL database";

# Deleting the PostgreSQL service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name=sonar_db)" ]; then
    message -1 "[INFO] Removing previous PostgeSQL SonarQube database container.";
    docker stop sonar_db;
    docker rm sonar_db;
fi

# Launching the PostgreSQL service
message -1 "[INFO] Launching the SonarQube PostgeSQL database service.";
docker-compose up -d sonar_db;
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The SonarQube PostgeSQL database service could not be initialized." 1;
fi

# Getting internal IP address.
POSTGRES_SONAR_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' sonar_db)"
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] Could not retrieve the local SonarQube PostgeSQL database IP address." 1;
else
    message -1 "[INFO] Using \"$POSTGRES_SONAR_IP\" as the SonarQube PostgeSQL database IP address.";
    export POSTGRES_SONAR_IP=${POSTGRES_SONAR_IP};
fi


# Sonar component
message 4 "[COMPONENT] SonarQube";

# Deleting the Sonar service if it was already been created: Brand-new container.
if [ "$(docker ps -aq -f name="sonar") | grep sonar" ]; then
    message -1 "[INFO] Removing previous SonarQube container.";
    docker rm --force sonar;
fi
# Launching the Sonar service
message -1 "[INFO] Launching the Sonar service.";
if [ "$FORCE_BUILD" == "true" ]; then
    message -1 "[INFO] Recreating Sonar image.";
    docker-compose build --build-arg POSTGRES_SONAR_IP=${POSTGRES_SONAR_IP} \
                         --build-arg SONAR_PORT=${SONAR_PORT} sonar;
    if [ $? != 0 ]; then
        exit_with_message 1 "[ERROR] The Sonar image could not be built." 1;
    fi
fi
docker-compose up -d sonar;
if [ $? != 0 ]; then
    exit_with_message 1 "[ERROR] The Sonar service could not be initialized." 1;
fi

# Displaying installation summary
echo "";
message 2 "[SUCCESS] Installation results:";
message 2 "\t• Jenkins: up"
message 2 "\t• Sonar: up"
message 2 "\t• Sonar (db): up"
echo ""