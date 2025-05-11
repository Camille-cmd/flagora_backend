from importlib import import_module
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware as DjangoSessionMiddleware
import logging
logger = logging.getLogger(__name__)


class SessionMiddleware(DjangoSessionMiddleware):
    """
    SessionMiddleware to remove sessionid cookie from Ninja responses (api).
    """

    def process_request(self, request):
        if 'Authorization' in request.headers.keys():
            session_key = request.headers.get('Authorization').split()[-1]
            request.session = self.SessionStore(session_key)
        else:
            session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
            request.session = self.SessionStore(session_key)

    def process_response(self, request, response):
        super().process_response(request, response)
        if request.resolver_match and "ninja" in request.resolver_match.app_names and response.cookies.get('sessionid'):
            del response.cookies['sessionid']

        return response
