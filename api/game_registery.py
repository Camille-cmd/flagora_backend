from api.services.game_modes.base_game import GameService
from core.models import UserCountryScore
from core.models.user_country_score import GameModes


class GameServiceRegistry:
    _registry: dict[GameModes, type[GameService]] = {}

    @classmethod
    def register(cls, game_mode: GameModes):
        def decorator(service_cls: type[GameService]):
            cls._registry[game_mode] = service_cls
            return service_cls

        return decorator

    @classmethod
    def get_game_service(cls, game_mode: GameModes) -> type[GameService]:
        try:
            return cls._registry[game_mode]
        except KeyError:
            return None
