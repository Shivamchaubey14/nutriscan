"""Root URL configuration."""

from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

from config.views import HealthView

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("health/", HealthView.as_view(), name="health"),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/scan/", include("scans.urls")),
    path("api/v1/log/", include("logs.urls")),
    path("api/v1/foods/", include("nutrition.urls")),
]
