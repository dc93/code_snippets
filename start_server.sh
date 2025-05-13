#!/bin/bash
cd /home/claudebypass/projects/code_snippets
source venv/bin/activate
export FLASK_ENV=production
export FLASK_PORT=9935
export PYTHONUNBUFFERED=1
export GUNICORN_BIND=0.0.0.0:9935

exec gunicorn wsgi:application --bind=0.0.0.0:9935 --workers=4