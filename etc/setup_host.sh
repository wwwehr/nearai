#!/bin/bash
set -ex

JASNAH_DATA=/home/setup/.jasnah

mkdir -p $JASNAH_DATA

# Download jasnah-cli
if [ ! -d "$JASNAH_DATA/jasnah-cli" ]; then
    git clone git@github.com:JasnahOrg/jasnah-cli.git $JASNAH_DATA/jasnah-cli
fi

# Update latest version
cd $JASNAH_DATA/jasnah-cli
git checkout main
git pull

# If binary is not available install it
jasnah-cli version || python3 -m pip install -e .

CURRENT_INSTALLATION=$(jasnah-cli location)

if [[ "$JASNAH_DATA" == "$CURRENT_INSTALLATION" ]]; then
    python3 -m pip install -e .
fi

jasnah-cli supervisor start
