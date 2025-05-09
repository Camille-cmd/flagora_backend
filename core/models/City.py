from django.db import models


class City(models.Model):
    name_fr = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)

    is_capital = models.BooleanField(
        default=False, help_text="Several cities can be capital cities of a country (e.g, South Africa)."
    )

    class Meta:
        ordering = ('name_en',)
        verbose_name_plural = 'cities'

    def __str__(self):
        return self.name_en
