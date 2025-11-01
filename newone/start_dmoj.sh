#!/bin/bash

# Change to the project directory
cd /home/lalith/Desktop/Test_demoj_1

# Activate the virtual environment
source dmojsite/bin/activate

# Change to the site directory
cd site

# Start the web server in the background
python3 manage.py runserver 0.0.0.0:8000 &

# Wait a few seconds to ensure the web server is up
sleep 3

# Start the judge server
dmoj -c judge.yml -p 9999 0.0.0.0