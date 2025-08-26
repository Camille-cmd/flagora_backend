from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import User
from core.models.user_country_score import GameModes


class UserPreferenceGameMode(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_preference_game_modes",
    )
    game_mode = models.CharField(max_length=255, choices=GameModes.choices)
    show_tips = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "game_mode")
        verbose_name = _("User preference by game mode")
        verbose_name_plural = _("User preference by game modes")

    def __str__(self):
        return self.user
