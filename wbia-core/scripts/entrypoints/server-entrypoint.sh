#!/bin/bash
exec gunicorn -b 0.0.0.0:5000 -w 1 --timeout 1200 sidecar.api:app
