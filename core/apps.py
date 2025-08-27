from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    # def ready(self):
    #     from django.db.backends.signals import connection_created
    #
    #     from api.flag_store import flag_store
    #     connection_created.connect(flag_store.reload_all_flags)
