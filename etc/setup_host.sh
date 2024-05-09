#!/bin/bash
set -e

JASNAH_DATA=/home/setup/.jasnah
CLI_PATH="$JASNAH_DATA/jasnah-cli"

mkdir -p $JASNAH_DATA

# Download jasnah-cli
if [ ! -d "$JASNAH_DATA/jasnah-cli" ]; then
    git clone git@github.com:JasnahOrg/jasnah-cli.git $CLI_PATH
fi

# Update latest version
cd $CLI_PATH
git checkout main
git pull

# If binary is not available install it
jasnah-cli version || python3 -m pip install -e .

CURRENT_INSTALLATION=$(jasnah-cli location)

if [[ "$CLI_PATH" == "$CURRENT_INSTALLATION" ]]; then
    python3 -m pip install -e .
fi

jasnah-cli supervisor install
jasnah-cli supervisor start
