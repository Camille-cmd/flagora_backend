from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import Country, Guess


class UserCountryScore(models.Model):
    class GameModes(models.TextChoices):
        GUESS_COUNTRY_FROM_FLAG = 'GUESS_COUNTRY_FROM_FLAG', _("Guess Country From Flag")
        GUESS_CAPITAL_FROM_COUNTRY = "GUESS_CAPITAL_FROM_COUNTRY", _("Guess Capital From Country")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="country_scores", verbose_name=_("country"))
    user = models.ForeignKey("core.User", on_delete=models.CASCADE, related_name="user_scores", verbose_name=_("user"))
    game_mode = models.CharField(choices=GameModes.choices, verbose_name=_("game mode"))
    user_guesses = models.ManyToManyField(Guess, blank=True, related_name="user_scores", verbose_name=_("user guesses"))

    class Meta:
        ordering = ("created_at",)
        unique_together = ("country", "game_mode", "user")
        verbose_name = _("user country score")
        verbose_name_plural = _("user country scores")

    def __str__(self):
        return f"{self.user.username} score for {self.country.iso2_code} - {self.game_mode}"

    def weight(self):
        pass
