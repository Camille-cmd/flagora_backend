docker exec -it flagora_backend coverage run manage.py test "$@"
docker exec -it flagora_backend coverage report -m

#docker exec -it flagora_backend coverage html
