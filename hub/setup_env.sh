#!/bin/bash

cd "$(dirname "$0")"/.. || exit

if [ ! -d "venv" ]; then
    python -m venv venv
fi

source venv/bin/activate

pip install -e .

echo "Setup complete"