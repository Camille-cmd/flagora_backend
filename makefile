# Name of the Django service in docker-compose.yml
SERVICE=flagora_backend

# Command runner
RUN=docker exec -it $(SERVICE)

# Create a superuser
createsuperuser:
	$(RUN) python manage.py createsuperuser

# Make migrations
makemigrations:
	$(RUN) python manage.py makemigrations

# Apply migrations
migrate:
	$(RUN) python manage.py migrate

# Open shell
shell:
	$(RUN) python manage.py shell
