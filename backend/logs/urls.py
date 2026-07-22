from django.urls import URLPattern, path

from logs.views import DailySummaryView, MealLogDetail, MealLogListCreate

urlpatterns: list[URLPattern] = [
    path("", MealLogListCreate.as_view(), name="log-list-create"),
    path("summary/", DailySummaryView.as_view(), name="log-summary"),
    path("<int:pk>/", MealLogDetail.as_view(), name="log-detail"),
]
