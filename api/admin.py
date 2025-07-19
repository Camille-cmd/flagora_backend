from django.contrib import admin

from core.models import UserCountryScore


@admin.register(UserCountryScore)
class UserCountryScoreAdmin(admin.ModelAdmin):
    pass
