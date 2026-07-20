from django.urls import URLPattern, path

from scans.views import FeedbackView, ScanView

urlpatterns: list[URLPattern] = [
    path("", ScanView.as_view(), name="scan"),
    path("<uuid:scan_id>/feedback/", FeedbackView.as_view(), name="scan-feedback"),
]
