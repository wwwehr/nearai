#!/bin/bash
exec /home/setup/.local/bin/gunicorn -w 4 -b 0.0.0.0:8100 jasnah.server:app
