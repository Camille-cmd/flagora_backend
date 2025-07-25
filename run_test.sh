# RuntimeWarning because of App ready imports
docker exec -it flagora_backend python -W ignore::RuntimeWarning -m coverage run manage.py test "$@"
docker exec -it flagora_backend coverage report -m

#docker exec -it flagora_backend python3 manage.py test "$@"

docker exec -it flagora_backend coverage html
