#!/bin/bash

cd "$(dirname "$0")"/.. || exit

source venv/bin/activate

cd hub || exit

fastapi run app.py --port 8001