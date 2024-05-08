#!/bin/bash
mkdir -p ~/.jasnah

# Download jasnah-cli
if [ ! -d "~/.jasnah/jasnah-cli" ]; then
    git clone git@github.com:JasnahOrg/jasnah-cli.git ~/.jasnah/jasnah-cli
fi

# Update latest version
cd ~/.jasnah/jasnah-cli
git checkout main
git pull

# Install jasnah-cli "binary"
python3 -m pip install -e .

jasnah-cli supervisor start
