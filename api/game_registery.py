from api.services.game_modes.base_game import GameService
from core.models import UserCountryScore


class GameServiceRegistry:
    _registry: dict[UserCountryScore.GameModes, type[GameService]] = {}

    @classmethod
    def register(cls, game_mode: UserCountryScore.GameModes):
        def decorator(service_cls: type[GameService]):
            print(f"Registering service: {service_cls.__name__}")
            cls._registry[game_mode] = service_cls
            return service_cls

        return decorator

    @classmethod
    def get_game_service(cls, game_mode: UserCountryScore.GameModes) -> type[GameService]:
        print(cls._registry)
        try:
            return cls._registry[game_mode]
        except KeyError:
            raise ValueError(f"Unsupported game mode: {game_mode}")
