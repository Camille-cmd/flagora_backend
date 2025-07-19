from django.http import HttpRequest
from django.utils import translation
from django.utils.translation import gettext as _
from ninja import Router

from api.schema import (
    CountriesOut,
    CountryOut,
    ResponseError,
    ResponseUserOut,
    UserLanguageSet,
    UserUpdate,
    UserUpdatePassword,
)
from core.models import Country, User

router = Router(by_alias=True)


@router.get("user/me", auth=None, response={200: ResponseUserOut, 401: ResponseError})
def user_me(request: HttpRequest):
    """ "
    Get the current user information.
    """
    # Tell frontend that the user is not authenticated
    if not request.user.is_authenticated:
        return 401, {"error_message": _("User not authenticated")}

    user = request.user
    return 200, user.user_out


@router.post("user/set-language", response={200: dict})
def user_set_language(request, payload: UserLanguageSet):
    """
    Set the language of the user.
    """
    request.user.language = payload.language
    request.user.save()

    translation.activate(payload.language)

    return 200, {}


@router.put("user/", response={200: ResponseUserOut, 400: ResponseError})
def user_update(request: HttpRequest, payload: UserUpdate):
    """
    Update the user information.
    """
    user = request.user

    if User.objects.exclude(pk=user.pk).filter(username__iexact=payload.username).exists():
        return 400, {"error_message": _("Username already registered")}

    user.username = payload.username
    user.save()

    return 200, user.user_out


@router.put("user/password", response={200: dict, 400: ResponseError})
def user_update_password(request: HttpRequest, payload: UserUpdatePassword):
    """
    Update the user password.
    """
    user = request.user

    if not user.check_password(payload.old_password):
        return 400, {"error_message": _("Old password is incorrect")}

    user.set_password(payload.new_password)
    user.save()

    return 200, {}


@router.get("country/list", response={200: CountriesOut}, auth=None)
def country_get_list(request: HttpRequest):
    """
    Return the list of all countries' names in the user-selected language.
    """
    language = request.LANGUAGE_CODE
    if request.user.is_authenticated:
        language = request.user.language
    name_field = f"name_{language}"
    countries_qs = Country.objects.all().values(name_field, "iso2_code").order_by(name_field)

    countries = []
    for country in countries_qs:
        country_out = CountryOut(name=country[name_field], iso2_code=country["iso2_code"])
        countries.append(country_out)

    return 200, CountriesOut(countries=countries)
