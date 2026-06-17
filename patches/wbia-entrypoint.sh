#!/bin/bash
set -e
export QT_QPA_PLATFORM=offscreen
export PYTHONUNBUFFERED=1
/virtualenv/env3/bin/python3 /patches/patch_wbia_schema.py
exec /virtualenv/env3/bin/python3 -m wbia.dev --dbdir /data/db --logdir /data/db/logs --web --containerized --production
