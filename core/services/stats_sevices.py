from datetime import datetime

from django.db.models import Count, Q
from django.utils import timezone

from api.flag_store import flag_store
from api.schema import CityOutStats, CountryOutStats, UserStats, UserStatsByGameMode
from api.utils import user_get_language
from core.models import Guess, User, UserCountryScore
from core.models.user_country_score import GameModes
from core.services.user_services import user_get_best_steak


def user_get_stats(user: User) -> UserStatsByGameMode:
    user_language = user_get_language(user)
    name_field = f"name_{user_language}"
    max_threshold = timezone.now() - timezone.timedelta(days=365)

    return [get_game_mode_stats(user, game_mode, name_field, max_threshold) for game_mode in GameModes.values]


def get_game_mode_stats(user: User, game_mode: str, name_field: str, max_threshold: datetime) -> UserStatsByGameMode:
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
    max_streak = user_get_best_steak(user, game_mode)

    # Annotated scores for most failed/correct analysis
    annotated_scores = user_scores.annotate(
        fails=Count("user_guesses", filter=Q(user_guesses__is_correct=False)),
        corrects=Count("user_guesses", filter=Q(user_guesses__is_correct=True)),
        total=Count("user_guesses"),
    )

    most_failed_obj = annotated_scores.order_by("-fails").first()
    most_correct_obj = annotated_scores.order_by("-corrects").first()

    # Create appropriate stats objects based on game mode
    most_failed, most_correct = create_stats_objects(game_mode, most_failed_obj, most_correct_obj, name_field)

    return UserStatsByGameMode(
        game_mode=game_mode,
        stats=UserStats(
            most_strikes=max_streak,
            success_rate=success_rate,
            most_failed=most_failed,
            most_correctly_guessed=most_correct,
        ),
    )


def calculate_success_rate(obj) -> float:
    """Calculate success rate for a score object."""
    if obj and obj.total:
        return round(obj.corrects / obj.total * 100, 2)
    return 0


def create_country_stats(country, name_field: str, success_rate: float = 0) -> CountryOutStats:
    """Create CountryOutStats object."""
    if not country:
        return CountryOutStats(flag="", name="", iso2_code="", success_rate=success_rate)

    return CountryOutStats(
        flag=flag_store.get_path(country.iso2_code) or "",
        name=getattr(country, name_field),
        iso2_code=country.iso2_code,
        success_rate=success_rate,
    )


def create_city_stats(score_obj, name_field: str) -> CityOutStats:
    """Create CityOutStats object."""
    if not score_obj:
        return CityOutStats(name=[""], success_rate=0, country=create_country_stats(None, name_field))

    country = score_obj.country
    city_name = country.get_capitals_names(name_field)
    success_rate = calculate_success_rate(score_obj)

    return CityOutStats(
        name=city_name,
        success_rate=success_rate,
        country=create_country_stats(country, name_field),
    )


def create_stats_objects(game_mode: str, most_failed_obj, most_correct_obj, name_field: str):
    """Create appropriate stats objects based on game mode."""
    guess_country_from_flag_modes = [gm for gm in GameModes.values if "GCFF" in gm]
    if game_mode in guess_country_from_flag_modes:
        most_failed = create_country_stats(
            most_failed_obj.country if most_failed_obj else None, name_field, calculate_success_rate(most_failed_obj)
        )
        most_correct = create_country_stats(
            most_correct_obj.country if most_correct_obj else None,
            name_field,
            calculate_success_rate(most_correct_obj),
        )
    else:  # capital guessing
        most_failed = create_city_stats(most_failed_obj, name_field)
        most_correct = create_city_stats(most_correct_obj, name_field)

    return most_failed, most_correct
