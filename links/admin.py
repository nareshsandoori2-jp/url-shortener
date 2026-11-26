from django.contrib import admin

from .models import Click, Link


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ("short_code", "original_url", "owner", "click_count", "is_active", "expires_at")
    search_fields = ("short_code", "original_url")


admin.site.register(Click)
