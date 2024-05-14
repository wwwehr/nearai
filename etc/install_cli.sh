#!/bin/bash
set -e

JASNAH_DATA=/home/setup/.jasnah
CLI_REPO="$JASNAH_DATA/jasnah-cli"
CLI_CMD="/home/setup/.local/bin/jasnah-cli"

mkdir -p $JASNAH_DATA

# Download jasnah-cli
if [ ! -d "$CLI_REPO" ]; then
    git clone git@github.com:nearai/jasnah-cli.git $CLI_REPO
fi

# Update latest version
cd $CLI_REPO
git checkout main
git pull

python3 -m pip install --upgrade pip
python3 -m pip install -e .
