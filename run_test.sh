#!/bin/bash
set -e

# Default: no coverage
WITH_COVERAGE=false

# Parse flags
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --coverage) WITH_COVERAGE=true ;;
        *) TEST_ARGS="$TEST_ARGS $1" ;;
    esac
    shift
done

if [ "$WITH_COVERAGE" = true ]; then
    echo "Running tests with coverage..."
    docker exec -it flagora_backend_dev python3 -m coverage run manage.py test --settings=flagora.settings_test $TEST_ARGS
    docker exec -it flagora_backend_dev coverage report -m
    docker exec -it flagora_backend_dev coverage html
else
    echo "Running tests without coverage..."
    docker exec -it flagora_backend_dev python3 manage.py test --settings=flagora.settings_test $TEST_ARGS
fi
