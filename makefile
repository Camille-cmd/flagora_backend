# Name of the Django service in docker-compose.yml
SERVICE=flagora_backend

# Command runner
RUN=docker exec -it $(SERVICE)

# Directories to ignore during makemessages
IGNORE_DIRS=\
  --ignore=htmlcov \
  --ignore=venv \
  --ignore=.venv \
  --ignore=node_modules \
  --ignore=static \
  --ignore=media \
  --ignore=migrations

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

makemessages:
	@echo "📝 Running makemessages..."
	./manage.py makemessages --all --no-obsolete $(IGNORE_DIRS)
