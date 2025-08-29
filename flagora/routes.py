import re

from django.http import FileResponse, HttpRequest
from django.utils.translation import gettext as _
from ninja import NinjaAPI
from ninja.security import django_auth

from api.schema import ResponseError
from core.models import Country

media_router_api = NinjaAPI(csrf=True, urls_namespace="media")


@media_router_api.get("/flags/{iso2_code}/flag.svg", auth=django_auth, response={200: str, 400: ResponseError})
def media_flags(request: HttpRequest, iso2_code: str):
    """
    This endpoint is used to serve flags within the admin.
    This is not to be used as an endpoint for serving flags outside the admin.
    """
    iso2_code_regex = r"^[A-Z]{2}$"
    if re.match(iso2_code_regex, iso2_code) is not None:
        country = Country.objects.get(iso2_code=iso2_code)
        return FileResponse(open(country.flag.path, "rb"), content_type="image/svg+xml")

    return 404, {"error_message": _("Country not found")}
