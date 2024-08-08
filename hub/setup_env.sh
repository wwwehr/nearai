#!/bin/bash

cd "$(dirname "$0")"/.. || exit

pyenv global 3.10.14
pyenv shell 3.10.14

if [ ! -d "venv" ]; then
    python -m venv venv
fi

source venv/bin/activate

pip install -e .

pip3.10 install unicorn fastapi base58 pynacl

echo "Setup complete"