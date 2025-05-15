from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from ninja import Router
from django.utils.translation import gettext as _
from api.schema import UserLanguageSet, ResponseUserOut, ResponseError

router = Router(by_alias=True)


@router.get("user/me", auth=None, response={ 200: ResponseUserOut, 401: ResponseError})
def user_me(request: HttpRequest):
    """"
    Get the current user information.
    """
    user = request.user
    if not user.is_authenticated:
        return 401, {"error": _("Not authenticated"), "code": "not_authenticated"}

    print(user.language)
    return 200, {"username": user.username, "email": user.email, "user_id": user.id, "language": user.language, "is_email_verified": user.is_email_verified}

@router.post("user/set-language", response={200: dict, 401: ResponseError})
def user_set_language(request, payload: UserLanguageSet):
    """
    Set the language of the user.
    """
    request.user.language = payload.language
    request.user.save()

    return 200, {}
