from ninja import NinjaAPI
from ninja.security import HttpBearer

from api.routes.api import router as api_router
from api.routes.auth import auth_router

# Using HttpBearer along with Django's session authentication
# The goal is to use django's session token as the bearer token
# See middleware.py for more information
class BearerAuth(HttpBearer):
    def authenticate(self, request, token):
        # Request has user set by Django's session authentication
        # We are using the sessionid cookie as the bearer token
        if request.user.is_authenticated:
            return request.user

        return None


api = NinjaAPI(auth=BearerAuth())

api.add_router("/v1", api_router)
api.add_router("/v1/auth/", auth_router)
