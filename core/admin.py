from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.utils.html import format_html
from django import forms

from core.models import Country, City
from core.services import country_update


class CapitalCitiesInline(admin.TabularInline):
    model = Country.cities.through
    extra = 0
    can_delete = False
    verbose_name_plural = "Capital Cities"

    def get_queryset(self, request):
        """
        Inline used to display the capital cities of a country.
        """
        qs = super().get_queryset(request)
        return qs.filter(city__is_capital=True)

class CountryAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Those fields can be null but not blank
        self.fields["flag"].required = False

    class Meta:
        model = Country
        fields = "__all__"

    def clean_flag(self):
        """
        Clean flag to accept null values.
        """
        flag = self.cleaned_data.get("flag", None)
        if not flag:
            return None  # Retourne explicitement None si aucun fichier n'est fourni
        return flag


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name_en", "display_flag", "continent")
    search_fields = ("name_en", "name_fr", "name_native")
    fields = ("name_en", "name_fr", "name_native", "continent", "iso2_code", "iso3_code", "wikidata_id", "display_flag", "flag")
    readonly_fields = ['display_flag']  # this is for the change form
    inlines = [CapitalCitiesInline]
    list_filter = [
        "continent",
    ]
    form = CountryAdminForm

    @admin.display(description="Flag")
    def display_flag(self, obj):
        """
        Génère le HTML pour afficher l'image du drapeau dans l'administration.
        """
        if obj.flag:  # Vérifiez si un drapeau est disponible
            return format_html(
                f'<img src="{obj.flag.url}" style="width: 80px; height: auto;" alt="Flag">'
            )
        return "(No Flag)"

    def get_urls(self):
        urls = super().get_urls()

        additional_urls = [
            path("<path:object_id>/update/", self.admin_site.admin_view(self.update), name="core_country_update"),
        ]

        return additional_urls + urls

    def update(self, request, object_id):
        """
        Update a country using Wikidata and redirect back to the detail page.
        """
        country = get_object_or_404(Country, pk=object_id)
        try:
            country_update(country)

            messages.success(request, f"The country '{country.name_en}' has been updated successfully!")
            messages.warning(request, "Note: native name is not a field that can be updated. Please update manually in the database if needed.")

        except Exception as e:
            messages.error(request, f"Failed to update the country '{country.name_en}': {str(e)}")

        # Redirect back to the detail page
        return redirect("admin:core_country_change", object_id)

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name_en",)
    search_fields = ("name_en", "name_fr")
