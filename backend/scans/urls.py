from django.urls import URLPattern, path

from scans.views import ScanView

urlpatterns: list[URLPattern] = [
    path("", ScanView.as_view(), name="scan"),
]
