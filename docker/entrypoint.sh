#!/bin/bash

# Collect static files
echo "Collect static files"
uv run manage.py collectstatic --noinput

# Apply database migrations
echo "Apply database migrations"
uv run manage.py migrate

# Start server
echo "Starting server $DJANGO_ENV"
if [ "$DJANGO_ENV" = "development" ]; then
   echo "Running development server"
  uv run manage.py runserver 0.0.0.0:8000
else

  echo "Running Daphne"
  uv run daphne flagora.asgi:application --bind 0.0.0.0 -p 8000
fi
