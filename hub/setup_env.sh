#!/bin/bash

cd "$(dirname "$0")"/.. || exit

pyenv shell 3.10.14

if [ ! -d "venv" ]; then
    python -m venv venv
fi

source venv/bin/activate

pip3.10 install -e .[hub]

echo "Setup complete"