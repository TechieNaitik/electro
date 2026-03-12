#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Use manage.py from myproject directory
python myproject/manage.py collectstatic --no-input
python myproject/manage.py migrate
