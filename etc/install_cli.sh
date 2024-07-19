#!/bin/bash
set -e

NEARAI_DATA=/home/setup/.nearai
CLI_REPO="$NEARAI_DATA/nearai-cli"
CLI_CMD="/home/setup/.local/bin/nearai-cli"

mkdir -p $NEARAI_DATA

# Download jasnah-cli
# TODO(#49): rename repo
if [ ! -d "$CLI_REPO" ]; then
    git clone git@github.com:nearai/jasnah-cli.git $CLI_REPO
fi

# Update latest version
cd $CLI_REPO
git checkout main
git pull

python3 -m pip install --upgrade pip
python3 -m pip install -e .
