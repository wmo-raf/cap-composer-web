#!/bin/bash

python manage.py migrate --noinput

python manage.py collectstatic --clear --no-input

# run gunicorn
gunicorn capsite.wsgi:application --bind 0.0.0.0:8000 --workers=${GUNICORN_NUM_OF_WORKERS:-2} --timeout=${GUNICORN_TIMEOUT:-300}
