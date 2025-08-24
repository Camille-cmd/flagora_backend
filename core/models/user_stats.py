from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models.user_country_score import GameModes


class UserStats(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    user = models.ForeignKey(
        "core.User",
        on_delete=models.CASCADE,
        related_name="user_stats",
        verbose_name=_("user"),
    )
    game_mode = models.CharField(choices=GameModes.choices, verbose_name=_("game mode"))

    best_streak = models.PositiveIntegerField(verbose_name=_("Best streak"), default=0)

    class Meta:
        ordering = ("created_at",)
        unique_together = ("user", "game_mode")
        verbose_name = _("user stat")
        verbose_name_plural = _("user stats")

    def __str__(self):
        return f"{self.user.username} stats for {self.game_mode}"
