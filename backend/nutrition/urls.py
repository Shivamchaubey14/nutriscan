from django.urls import URLPattern, path

from nutrition.views import FoodSearchView

urlpatterns: list[URLPattern] = [
    path("search/", FoodSearchView.as_view(), name="food-search"),
]
