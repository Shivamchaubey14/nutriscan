"""Manual food search over the nutrition DB (for correcting/logging by name)."""

from django.db.models import QuerySet
from rest_framework import generics

from nutrition.models import Food
from nutrition.serializers import FoodSerializer

MAX_RESULTS = 20


class FoodSearchView(generics.ListAPIView[Food]):
    serializer_class = FoodSerializer

    def get_queryset(self) -> QuerySet[Food]:
        # MySQL: case-insensitive LIKE. A fulltext index is the scale-up path
        # (the SRS's Postgres trigram equivalent).
        query = self.request.query_params.get("q", "").strip()
        if not query:
            return Food.objects.none()
        return Food.objects.filter(name__icontains=query).order_by("name")[:MAX_RESULTS]
