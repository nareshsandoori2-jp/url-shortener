from django.contrib import admin
from django.urls import include, path, re_path

from links.views import redirect_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("links.urls")),
    re_path(r"^(?P<code>[0-9A-Za-z_-]{3,20})/$", redirect_view, name="redirect"),
]
