from importlib import import_module

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        from django.db.backends.signals import connection_created

        # Import to trigger @register decorators
        def setup_game_services(sender, **kwargs):
            import_module("api.services.game_modes")

        connection_created.connect(setup_game_services)
