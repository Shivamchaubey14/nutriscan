from django.urls import URLPattern, path

from logs.views import DailySummaryView, MealLogListCreate

urlpatterns: list[URLPattern] = [
    path("", MealLogListCreate.as_view(), name="log-list-create"),
    path("summary/", DailySummaryView.as_view(), name="log-summary"),
]
