from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import Country, Guess


class UserCountryScore(models.Model):
    class GameModes(models.TextChoices):
        GUESS_COUNTRY_FROM_FLAG = 'GUESS_COUNTRY_FROM_FLAG', _("Guess Country From Flag")
        GUESS_CAPITAL_FROM_COUNTRY = "GUESS_CAPITAL_FROM_COUNTRY", _("Guess Capital From Country")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    game_mode = models.CharField(choices=GameModes.choices)
    user_guesses = models.ManyToManyField(Guess, blank=True, related_name="user_guesses")

    class Meta:
        ordering = ("created_at",)
        unique_together = ("country", "game_mode", "user")

    def __str__(self):
        return f"{self.user.username} score for {self.country.iso2_code} - {self.game_mode}"

    def weight(self):
        pass
