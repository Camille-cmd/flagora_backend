## Première installation

Requiers python 3.13, uv et direnv

```bash
uv sync
```

```direnv allow```

Si direnv n'est pas installé, ou si on ne veut pas l'utiliser

```bash
source .venv/bin/activate
```

## Installation avec docker

```bash
docker compose up --build
```

## Importer les données

Pour la toute première fois, il faut importer les pays et les régions.
```bash
docker exec -it flagora_backend python manage.py import_countries
```

Le fichier `initial_data.json` contient les pays et les régions, mais pas les fichiers images des drapeaux. 
Utile si l'on veut écraser la base de données et recommencer à zéro sans refaire de call api.
```bash
docker exec -it flagora_backend python manage.py import_countries_from_json --file_name 'initial_data.json'
```

## Development shortcuts

Run Django management commands via Makefile:

```bash
make createsuperuser        # Create a superuser
make makemigrations         # Create new migrations
make migrate                # Apply migrations
make manage ARGS="shell"    # Run an arbitrary manage.py command
