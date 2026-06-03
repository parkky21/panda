#!/bin/bash
if [ "$#" -lt 2 ]; then
    echo "Usage: delayed_ping <name> <seconds>"
    exit 1
fi

NAME="$1"
SECONDS="$2"

sleep "$SECONDS"
echo "Ping for $NAME!"