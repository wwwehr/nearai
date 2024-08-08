#!/bin/bash

source venv/bin/activate

cd hub || exit

fastapi run app.py --port 8085