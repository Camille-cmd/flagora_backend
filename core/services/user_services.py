from core.models import User, UserStats
from core.models.user_country_score import GameModes


def user_get_beast_steak(user: User, game_mode: GameModes) -> int:
    try:
        return UserStats.objects.get(user=user, game_mode=game_mode).best_streak
    except UserStats.DoesNotExist:
        return 0
