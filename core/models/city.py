from django.db import models
from django.utils.translation import gettext_lazy as _

class City(models.Model):
    name_fr = models.CharField(max_length=100, verbose_name=_("French name"))
    name_en = models.CharField(max_length=100, verbose_name=_("English name"))

    is_capital = models.BooleanField(
        default=False,
        verbose_name=_("Is capital city"),
        help_text=_("Several cities can be capital cities of a country (e.g, South Africa).")
    )

    class Meta:
        ordering = ('name_en',)
        verbose_name = _('city')
        verbose_name_plural = _('cities')

    def __str__(self):
        return self.name_en
