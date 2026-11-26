from django.conf import settings
from django.db import models


class Link(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="links"
    )
    original_url = models.URLField(max_length=2000)
    short_code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    click_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"


class Click(models.Model):
    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name="clicks")
    clicked_at = models.DateTimeField(auto_now_add=True)
    user_agent = models.CharField(max_length=300, blank=True)
    referrer = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"Click on {self.link_id} at {self.clicked_at}"
