from ninja import NinjaAPI
from ninja.security import django_auth

from api.api import router as api_router
from api.auth import auth_router
api = NinjaAPI(auth=django_auth)

api.add_router("/v1", api_router)
api.add_router("/v1/auth/", auth_router)
