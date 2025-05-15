from django.db import models
from django.utils.translation import gettext_lazy as _

class Guess(models.Model):
    created_at = models.DateTimeField(db_index=True, auto_now_add=True, verbose_name=_("created at"))
    is_correct = models.BooleanField(verbose_name=_("is correct"))

    class Meta:
        ordering = ("created_at",)
        verbose_name = _("guess")
        verbose_name_plural = _("guesses")

    def __str__(self):
        return f"{self.is_correct} on {str(self.created_at)}"

    def weight(self):
        pass
