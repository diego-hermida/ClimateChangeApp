#! /bin/bash

# ---------- Functions ---------- #

source "./utilities/bash_util.sh"

# Displays script usage and exits.
# :param $1: Exit code.
function usage () {
    exit_with_message 1 "Installs and executes the Telegram Configurator component.
         \n\n> usage: install.sh [-h] [--help] [--version ] [--deploy-args \"<args>\"] [--force-build] [--no-run]
         \n\t[--perform-deploy-actions]
         \n• -h, --help: shows this message.
         \n --version: displays app's version.
         \n• --deploy-args \"<args>\": enables \"Expert Mode\", allowing to pass custom args to the deploy script.
         \n\t  Defaults to \"--with-tests\". Must be used in conjunction with --perform-deploy-actions.
         \n• --force-build: builds the Telegram Configurator image even if it already exists.
         \n• --no-run: does not execute the Configurator after building it.
         \n• --perform-deploy-actions : installs the application performing all deploy steps. By default, deploy
         \n\t  steps are skipped." $1;
}


# ---------- Definitions ---------- #

# Setting default values
DEPLOY_ARGS=null;
SKIP_DEPLOY=true;
FORCE_BUILD=false;
RUN=true;


# ---------- Argument manipulation ---------- #

# Parsing arguments
EXPECTED_INPUT=":h-:"
while getopts "$EXPECTED_INPUT" ARG; do
    case ${ARG} in
        h) usage 0 ;;
        -) case ${OPTARG} in
                help) usage 0 ;;
                version) show_app_version ;;
                force-build) FORCE_BUILD=true ;;
                deploy-args)
                    VAL="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ));
                    ensure_not_empty  "--deploy-args" ${VAL};
                    DEPLOY_ARGS=${VAL};
                ;;
                no-run) RUN=false ;;
                perform-deploy-actions) SKIP_DEPLOY=false ;;
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
        message -1 "[INFO] Deploy operations will be skipped for the Telegram Configurator component.";
        DEPLOY_ARGS="--skip-all"
    elif [ "$DEPLOY_ARGS" == "null" ]; then
        message -1 "[INFO] Using default values for DEPLOY_ARGS.";
        DEPLOY_ARGS="--with-tests";
fi

if [ "$RUN" == "false" ]; then
    message -1 "[INFO] The Telegram Configurator will not be executed."
fi


# ---------- Installation ---------- #

# Enables compatibility with docker-compose.yml
export BIND_IP_ADDRESS='0.0.0.0';

# Telegram Configurator component
message 4 "[COMPONENT] Telegram Configurator";

# Building the Telegram Configurator component
if [ "$(docker image ls | grep telegram_bot | wc -c | tr -d ' ')" == 0 ] || [ "$FORCE_BUILD" == "true" ]; then
    docker-compose build --build-arg DEPLOY_ARGS="${DEPLOY_ARGS}" telegram_bot;
    if [ $? != 0 ]; then
        exit_with_message 1 "> The Telegram Configurator image could not be built." 1;
    fi
    else message -1 "[INFO] Running pre-built Telegram Configurator Docker image.";
fi

# Running the Telegram Configurator component
if [ "$RUN" == "true" ]; then
    message -1 "[INFO] Running the Telegram Configurator component.";
    echo "";
    docker run --rm -i -t --name telegram_bot diegohermida/telegram_bot:latest;

    # Displaying installation summary
    if [ $? != 0 ]; then
            exit_with_message 1 "\n[ERROR] The Telegram Configurator did not exit normally. You should rerun this installer." 1;
       else exit_with_message 2 "\n[SUCCESS] The Telegram Configurator was successful." 0;
    fi
    echo ""
fi
