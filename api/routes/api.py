from django.http import HttpRequest
from django.utils import translation
from django.utils.translation import gettext as _
from ninja import Router

from api.schema import (
    ResponseError,
    ResponseUserOut,
    UserLanguageSet,
    UserStatsByGameMode,
    UserUpdate,
    UserUpdatePassword,
    UserUpdatePreferences,
)
from api.utils import user_get_language
from core.models import City, Country, Department, User, UserPreferenceGameMode
from core.services.stats_sevices import user_get_stats

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


@router.put("user/me/", response={200: ResponseUserOut, 401: ResponseError})
def user_me_preferences(request: HttpRequest, payload: UserUpdatePreferences):
    """Set user preferences"""
    user = request.user
    # Create or update the user preferences (only show_tips for now)
    UserPreferenceGameMode.objects.update_or_create(
        user=user, game_mode=payload.game_mode, defaults={"show_tips": payload.show_tips}
    )
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


@router.get("country/list", response={200: dict[str, str]}, auth=None)
def country_get_list(request: HttpRequest):
    """
    Return the list of all countries' names in the user-selected language.
    """
    user_language = user_get_language(request.user)
    name_field = f"name_{user_language}"
    countries_qs = Country.objects.all().values(name_field, "iso2_code").order_by(name_field)

    countries = {}
    for country in countries_qs:
        countries[country[name_field]] = country["iso2_code"]

    return 200, countries


@router.get("city/list", response={200: dict[str, int]}, auth=None)
def city_get_list(request: HttpRequest):
    """
    Return the list of all cities' names in the user-selected language.
    """
    user_language = user_get_language(request.user)
    name_field = f"name_{user_language}"
    cities_qs = City.objects.all().values(name_field, "pk").order_by(name_field)

    cities = {}
    for city in cities_qs:
        cities[city[name_field]] = city["pk"]

    return 200, cities


@router.get("department/list", response={200: dict[str, str]}, auth=None)
def department_get_list(request: HttpRequest):
    """
    Return the list of all French departments' names.
    """
    departments_qs = Department.objects.all().values("name", "number").order_by("number")

    departments = {}
    for department in departments_qs:
        departments[department["name"]] = department["number"]

    return 200, departments


@router.get("user/stats", response={200: list[UserStatsByGameMode]})
def user_stats(request: HttpRequest):
    stats = user_get_stats(request.user)
    return 200, stats
