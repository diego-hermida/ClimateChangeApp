#!/bin/bash

# ---------- Functions ---------- #

source "./utilities/bash_util.sh";

# Displays script usage and exits.
# :param $1: Exit code.
function usage () {
    exit_with_message 1 " Removes Docker containers/images whose tag matches the regular expression \".*_ci.*\". Examples:
                           \n\t foo/baz:latest       \t-\t    not removed
                           \n\t foo/baz:1.0          \t\t-\t    not removed
                           \n\t foo/baz:latest_ci    \t-\t      removed
                           \n\t foo/baz:1.0_ci       \t-\t    removed
            \n\n> usage: remove_docker_ci.sh [-h] [--help] [--version]
            \n• -h, --help: shows this message.
            \n• --version: displays app's version." $1;
}


# ---------- Argument manipulation ---------- #

EXPECTED_INPUT=":h-:"
while getopts "$EXPECTED_INPUT" ARG; do
    case "${ARG}" in
        h) usage 0 ;;
        -) case ${OPTARG} in
                help) usage 0 ;;
                version) show_app_version ;;
                :) exit_with_message 1 "Illegal option: \"--$OPTARG\" requires an argument" >&2 ;;
                *) exit_with_message 1 "Unrecognized option: --$OPTARG" >&2 ;;
            esac
        ;;
        :) exit_with_message 1 "Illegal option: \"-$OPTARG\" requires an argument" >&2 ;;
        *) exit_with_message 1 "Unrecognized option: -$OPTARG" >&2 ;;
    esac
done


# ---------- Actions ---------- #

# Remove Docker CI containers
message 4 "[ACTION] Removing all Docker CI containers.";

CONTAINERS=$(docker ps -aq -f name="_ci" | tr '\n' ' ' | awk '{$1=$1};1');
if [ "$CONTAINERS" != "" ]; then
    docker rm --force ${CONTAINERS};
    if [ $? != 0 ]; then
        message 1 "[ERROR] An error occurred while removing Docker CI containers.";
    else
        message 2 "[SUCCESS] Docker CI container(s) successfully removed.";
    fi
else
    message -1 "[INFO] No Docker CI containers were available to remove.";
fi

# Remove Docker CI images
message 4 "[ACTION] Removing all Docker CI images.";

IMAGES=$(docker images | grep "_ci" | tr -s ' ' | cut -d ' ' -f 3 | tr '\n' ' ' | awk '{$1=$1};1');
if [ "$IMAGES" != "" ]; then
    docker rmi --force ${IMAGES};
    if [ $? != 0 ]; then
        message 1 "[ERROR] An error occurred while removing Docker CI images.";
    else
        message 2 "[SUCCESS] Docker CI image(s) successfully removed.";
    fi
else
    message -1 "[INFO] No Docker CI images were available to remove.";
fi
echo ""
