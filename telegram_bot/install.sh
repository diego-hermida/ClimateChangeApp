#! /bin/bash

# ---------- Definitions ---------- #

# Setting default values
TELEGRAM_CONFIGURATOR_DEPLOY_ARGS=null;
SKIP_DEPLOY=true;
FORCE_BUILD=false;
RUN=true;

# Exits the installation process, but prints a message to command line before doing so.
# :param $1: Colour of the output line. This will be reset before exiting.
#            If this value equals -1, the default color is used.
# :param $2: Message to be printed.
# :param $3: Exit code.
function exit_with_message () {
    if [ $1 != -1 ]; then
        tput setaf $1;
    fi
    tput bold;
    echo -e $2;
    tput sgr0;
    echo ""
    exit $3;
}

# Prints a message. Message output uses bold by default.
# :param $1: Colour of the output line. This will be reset before exiting.
#            If this value equals -1, the default color is used.
# :param $2: Message to be printed.
function message () {
    tput bold;
    if [ $1 != -1 ]; then
        tput setaf $1;
    fi
    echo -e $2
    tput sgr0;
}

# ---------- Argument manipulation ---------- #

# Parsing arguments
for ARGUMENT in "$@"
do
    KEY=$(echo $ARGUMENT | cut -f1 -d=)
    VALUE=$(echo $ARGUMENT | cut -f2 -d=)
    case "$KEY" in
            FORCE_BUILD)                            FORCE_BUILD=${VALUE} ;;
            SKIP_DEPLOY)                            SKIP_DEPLOY=${VALUE} ;;
            TELEGRAM_CONFIGURATOR_DEPLOY_ARGS)      TELEGRAM_CONFIGURATOR_DEPLOY_ARGS=${VALUE} ;;
            *)
    esac
done

# Setting variables to lower case
SKIP_DEPLOY=echo "$SKIP_DEPLOY" | tr '[:upper:]' '[:lower:]';
FORCE_BUILD=echo "$FORCE_BUILD" | tr '[:upper:]' '[:lower:]';
TELEGRAM_CONFIGURATOR_DEPLOY_ARGS=echo "$TELEGRAM_CONFIGURATOR_DEPLOY_ARGS" | tr '[:upper:]' '[:lower:]';


# Warnings
if [ "$TELEGRAM_CONFIGURATOR_DEPLOY_ARGS" != "null" ] && [ "$SKIP_DEPLOY" == "true" ]; then
    message 3 "[WARNING] Parameter TELEGRAM_CONFIGURATOR_DEPLOY_ARGS has been set, but SKIP_DEPLOY is true.
              The value will be overridden to \"--skip-all\".";
    elif [ "$SKIP_DEPLOY" == "true" ]; then
        message -1 "[INFO] Deploy operations will be skipped for the Telegram Configurator component.";
        TELEGRAM_CONFIGURATOR_DEPLOY_ARGS="--skip-all"
    elif [ "$TELEGRAM_CONFIGURATOR_DEPLOY_ARGS" == "null" ]; then
        message -1 "[INFO] Using default values for TELEGRAM_CONFIGURATOR_DEPLOY_ARGS.";
        TELEGRAM_CONFIGURATOR_DEPLOY_ARGS="--with-tests";
fi

if [ "$RUN" == "false" ]; then
    message -1 "[INFO] The Telegram Configurator will not be executed."
fi

if ([ "$SKIP_DEPLOY" != "true" ] && [ "$SKIP_DEPLOY" != "false" ]) ||
   ([ "$FORCE_BUILD" != "true" ] && [ "$FORCE_BUILD" != "false" ]) ||
   ([ "$RUN" != "true" ] && [ "$RUN" != "false" ]); then
     exit_with_message 1 "> usage: install.sh [FORCE_BUILD=true] [SKIP_DEPLOY=false] [RUN=false]
                            [TELEGRAM_CONFIGURATOR_DEPLOY_ARGS=<args>]
                         \n\t- FORCE_BUILD: builds the Telegram Configurator image even if it already exists. Defaults
                               to \"false\".
                         \n\t- SKIP_DEPLOY: omits all deploy steps. Defaults to \"true\".
                         \n\t- RUN: executes the Configurator after building it. Defaults to \"true\".
                         \n\t- TELEGRAM_CONFIGURATOR_DEPLOY_ARGS: enables \"Expert Mode\", allowing to pass custom
                               args to the deploy script. Defaults to \"--with-tests\".
                         \nIMPORTANT: TELEGRAM_CONFIGURATOR_DEPLOY_ARGS must be used in conjunction with
                                      SKIP_DEPLOY=false." 1;
fi


# ---------- Installation ---------- #


# Telegram Configurator component
message 4 "[COMPONENT] Building the Telegram Configurator component.";

# Building the Data Gathering Subsystem component
if [ "$(docker image ls | grep telegram_bot | wc -c | tr -d ' ')" == 0 ] || [ "$FORCE_BUILD" == "true" ]; then
    docker-compose build --build-arg DEPLOY_ARGS="${TELEGRAM_CONFIGURATOR_DEPLOY_ARGS}" telegram_bot;
    if [ $? != 0 ]; then
        exit_with_message 1 "> The Telegram Configurator image could not be built." 1;
    fi
    else message -1 "[INFO] Running pre-built Telegram Configurator Docker image.";
fi

# Running the Telegram Configurator component
if [ "$RUN" == "true" ]; then
    message -1 "[INFO] Running the Telegram Configurator component.";
    echo "";
    docker run --rm -i -t --name telegram_bot diegohermida/telegram_bot:1.0;
fi

# Displaying installation summary
if [ $? != 0 ]; then
        exit_with_message 1 "\n[ERROR] The Telegram Configurator did not exit normally. You should rerun this installer." 1;
   else exit_with_message 2 "\n[SUCCESS] The Telegram Configurator was successful." 0;
fi
echo ""