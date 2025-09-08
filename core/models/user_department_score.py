from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import Department, Guess
from core.models.user_country_score import GameModes


class UserDepartmentScore(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="department_scores",
        verbose_name=_("department"),
    )
    user = models.ForeignKey(
        "core.User",
        on_delete=models.CASCADE,
        related_name="user_department_scores",
        verbose_name=_("user"),
    )
    game_mode = models.CharField(choices=GameModes.choices, verbose_name=_("game mode"))
    user_guesses = models.ManyToManyField(Guess, blank=True, related_name="user_department_scores", verbose_name=_("user guesses"))

    class Meta:
        ordering = ("created_at",)
        unique_together = ("department", "game_mode", "user")
        verbose_name = _("user department score")
        verbose_name_plural = _("user department scores")

    def __str__(self):
        return f"{self.user.username} score for {self.department.number} - {self.game_mode}"