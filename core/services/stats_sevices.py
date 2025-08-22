from datetime import datetime

from django.db.models import Count, Q
from django.utils import timezone

from api.flag_store import flag_store
from api.schema import CityOutStats, CountryOutStats, UserStats, UserStatsByGameMode
from api.utils import user_get_language
from core.models import Guess, User, UserCountryScore


def user_get_stats(user: User) -> UserStatsByGameMode:
    user_language = user_get_language(user)
    name_field = f"name_{user_language}"
    max_threshold = timezone.now() - timezone.timedelta(days=365)

    return [
        _get_game_mode_stats(user, game_mode, name_field, max_threshold)
        for game_mode in UserCountryScore.GameModes.values
    ]


def _get_game_mode_stats(user: User, game_mode: str, name_field: str, max_threshold: datetime) -> UserStatsByGameMode:
    """Get statistics for a specific game mode."""
    user_scores = UserCountryScore.objects.filter(user=user, game_mode=game_mode)
    user_guesses = Guess.objects.filter(
        user_scores__in=user_scores,
        created_at__gt=max_threshold,
    ).order_by("created_at")

    # Basic statistics
    total = user_guesses.count()
    correct = user_guesses.filter(is_correct=True).count()
    success_rate = round(correct / total * 100, 2) if total else 0
    max_streak = _calculate_max_streak(user_guesses)

    # Annotated scores for most failed/correct analysis
    annotated_scores = user_scores.annotate(
        fails=Count("user_guesses", filter=Q(user_guesses__is_correct=False)),
        corrects=Count("user_guesses", filter=Q(user_guesses__is_correct=True)),
        total=Count("user_guesses"),
    )

    most_failed_obj = annotated_scores.order_by("-fails").first()
    most_correct_obj = annotated_scores.order_by("-corrects").first()

    # Create appropriate stats objects based on game mode
    most_failed, most_correct = _create_stats_objects(game_mode, most_failed_obj, most_correct_obj, name_field)

    return UserStatsByGameMode(
        game_mode=game_mode,
        stats=UserStats(
            most_strikes=max_streak,
            success_rate=success_rate,
            most_failed=most_failed,
            most_correctly_guessed=most_correct,
        ),
    )


def _calculate_max_streak(user_guesses) -> int:
    """Calculate the maximum correct streak from guesses."""
    streak = max_streak = 0
    for guess in user_guesses:
        if guess.is_correct:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def _calculate_success_rate(obj) -> float:
    """Calculate success rate for a score object."""
    if obj and obj.total:
        return round(obj.corrects / obj.total * 100, 2)
    return 0


def _create_country_stats(country, name_field: str, success_rate: float = 0) -> CountryOutStats:
    """Create CountryOutStats object."""
    if not country:
        return CountryOutStats(flag="", name="", iso2_code="", success_rate=success_rate)

    return CountryOutStats(
        flag=flag_store.get_path(country.iso2_code) or "",
        name=getattr(country, name_field),
        iso2_code=country.iso2_code,
        success_rate=success_rate,
    )


def _create_city_stats(score_obj, name_field: str) -> CityOutStats:
    """Create CityOutStats object."""
    if not score_obj:
        return CityOutStats(name=[""], success_rate=0, country=_create_country_stats(None, name_field))

    country = score_obj.country
    city_name = country.get_capitals_names(name_field)
    success_rate = _calculate_success_rate(score_obj)

    return CityOutStats(
        name=city_name,
        success_rate=success_rate,
        country=_create_country_stats(country, name_field),
    )


def _create_stats_objects(game_mode: str, most_failed_obj, most_correct_obj, name_field: str):
    """Create appropriate stats objects based on game mode."""
    if game_mode == UserCountryScore.GameModes.GUESS_COUNTRY_FROM_FLAG:
        most_failed = _create_country_stats(
            most_failed_obj.country if most_failed_obj else None, name_field, _calculate_success_rate(most_failed_obj)
        )
        most_correct = _create_country_stats(
            most_correct_obj.country if most_correct_obj else None,
            name_field,
            _calculate_success_rate(most_correct_obj),
        )
    else:  # capital guessing
        most_failed = _create_city_stats(most_failed_obj, name_field)
        most_correct = _create_city_stats(most_correct_obj, name_field)

    return most_failed, most_correct
