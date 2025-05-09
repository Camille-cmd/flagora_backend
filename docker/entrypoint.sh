#!/bin/bash

# Collect static files
echo "Collect static files"
uv run manage.py collectstatic --noinput

# Apply database migrations
echo "Apply database migrations"
uv run manage.py migrate

# Start server
echo "Running development server"
uv run manage.py runserver 0.0.0.0:8000
