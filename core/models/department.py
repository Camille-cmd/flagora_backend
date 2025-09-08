from django.db import models
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    """
    French Department model for the guessing game.
    """
    name = models.CharField(max_length=100, verbose_name=_("Department name"))
    number = models.CharField(max_length=3, unique=True, verbose_name=_("Department number"))
    region = models.CharField(max_length=100, verbose_name=_("Region"))
    prefecture = models.CharField(max_length=100, verbose_name=_("Prefecture"))
    
    class Meta:
        ordering = ("number",)
        verbose_name = _("department")
        verbose_name_plural = _("departments")

    def __str__(self):
        return f"{self.number} - {self.name}"