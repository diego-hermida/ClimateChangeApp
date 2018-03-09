#!/bin/bash

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


# ---------- Actions ---------- #

# Remove Docker CI containers
message 4 "[ACTION] Removing all Docker CI containers.";
CONTAINERS=$(docker ps -aq -f name="_CI" | tr '\n' ' ' | awk '{$1=$1};1');
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
IMAGES=$(docker images | grep "_CI" | tr -s ' ' | cut -d ' ' -f 3 | tr '\n' ' ' | awk '{$1=$1};1');
if [ "$IMAGES" != "" ]; then
    docker rmi ${IMAGES};
    if [ $? != 0 ]; then
        message 1 "[ERROR] An error occurred while removing Docker CI images.";
    else
        message 2 "[SUCCESS] Docker CI container(s) successfully removed.";
    fi
else
    message -1 "[INFO] No Docker CI images were available to remove.";
fi
echo ""
