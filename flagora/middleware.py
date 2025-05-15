from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware as DjangoSessionMiddleware
import logging
logger = logging.getLogger(__name__)


class SessionMiddleware(DjangoSessionMiddleware):
    """
    Custom SessionMiddleware for token-based API authentication using Django sessions.

    We want to use Django's session backend for authentication, but as a token-based authentication.

    What this middleware does:
    - Uses the session ID passed in the `Authorization` header instead of reading it from the `sessionid` cookie.
    - Prevents Django from setting the `sessionid` cookie in API responses (to avoid CSRF-related constraints).

    Why:
    - By avoiding the session cookie, we also avoid Django's default CSRF checks.
    - This gives us stateless, token-like authentication behavior using the session backend.

    Summary:
    - Request: extracts the session ID from the Authorization header and attaches it to the request.
    - Response: removes the `sessionid` cookie if Django tries to set it (for API routes only).
    """

    def process_request(self, request):
        # Retrieve the session key from the Authorization header if present and set it to the request
        # otherwise fall back to the sessionid cookie (for admin).
        if 'Authorization' in request.headers.keys():
            session_key = request.headers.get('Authorization').split()[-1]
            request.session = self.SessionStore(session_key)
        else:
            session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
            request.session = self.SessionStore(session_key)

    def process_response(self, request, response):
        super().process_response(request, response)

        # For API requests handled by Django Ninja, remove the sessionid cookie from the response.
        # This ensures the frontend never receives or stores a session cookie.
        # The admin is still using the sessionid cookie, so we don't remove it for admin requests.
        if request.resolver_match and "ninja" in request.resolver_match.app_names and response.cookies.get('sessionid'):
            del response.cookies['sessionid']

        return response
