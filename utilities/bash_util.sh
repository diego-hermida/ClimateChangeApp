#! /bin/bash


# Exits the installation process, but prints a message to command line before doing so.
# :param $1: Colour of the output line. This will be reset before exiting.
#            If this value equals -1, the default color is used.
# :param $2: Message to be printed.
# :param $3: Exit code.
function exit_with_message () {
    if [ $1 != -1 ]; then
        tput -T xterm-256color setaf $1;
    fi
    tput -T xterm-256color bold;
    echo -e $2;
    tput -T xterm-256color sgr0;
    echo ""
    exit $3;
}


# Prints a message. Message output uses bold by default.
# :param $1: Colour of the output line. This will be reset before exiting.
#            If this value equals -1, the default color is used.
# :param $2: Message to be printed.
function message () {
    tput -T xterm-256color bold;
    if [ $1 != -1 ]; then
        tput -T xterm-256color setaf $1;
    fi
    echo -e $2
    tput -T xterm-256color sgr0;
}


# Ensures that an option's argument is not empty.
# :param $1: Option's name.
# :param $2: Option's argument (this is what will be checked).
function ensure_not_empty () {
    if [ "$2" == "" ]; then
        exit_with_message 1 "Illegal option: \"$1\" requires an argument." 2
    fi
}


# Ensures that an option's argument is a positive integer.
# :param $1: Option's name.
# :param $2: Option's argument (this is what will be checked).
function ensure_positive_integer () {
    if ! [[ $2 =~ ^[+]?[0-9]+$ ]]; then
        exit_with_message 1 "Illegal option: \"$1\" requires a positive integer as its argument." 2
    fi
}


# Calculates all IPv4 addresses.
function get_all_ip_addresses () {
    ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'
}


# Gets the last IPv4 address of the list of IPv4 addresses.
function get_ip_address () {
   get_all_ip_addresses | tail -n 1
}


# Displays all IPv4 addresses and exits.
function show_ip_addresses () {
    get_all_ip_addresses
    exit 0
}


# Displays application's version and exits.
function show_app_version () {
    echo "Climate Change App, version 2.6 (2018.4)"
    exit 0
}