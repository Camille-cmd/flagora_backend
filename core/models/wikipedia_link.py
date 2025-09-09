from django.db import models
from django.utils.translation import gettext_lazy as _


def build_wikipedia_link(target, language):
    return f"https://{language}.wikipedia.org/wiki/{target}"


class WikipediaLink(models.Model):
    """Abstract model to add a wikipedia link to a model"""

    wikipedia_link_fr = models.URLField(verbose_name=_("French Wikipedia Link"))
    wikipedia_link_en = models.URLField(verbose_name=_("English Wikipedia Link"))

    class Meta:
        abstract = True

    @classmethod
    def get_wikipedia_field_name(cls) -> str:
        """
        Return the name of the field to use to build the wikipedia link without language indication.

        For example, "name" for Country
        """
        raise NotImplementedError

    @classmethod
    def build_wikipedia_link(cls, target_value: str, language: str) -> str:
        return f"https://{language}.wikipedia.org/wiki/{target_value}"
