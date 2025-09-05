from .settings import *  # noqa

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "ERROR",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",  # only log 500 errors, not 4xx
            "propagate": False,
        },
    },
}
