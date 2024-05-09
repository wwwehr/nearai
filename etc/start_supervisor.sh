#!/bin/bash
exec gunicorn -w 4 -b 0.0.0.0:8000 jasnah.supervisor:app
