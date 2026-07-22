"""Meal logging + daily calorie summary."""

from datetime import date as date_type
from typing import Any

from accounts.models import User
from django.db.models import QuerySet, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from logs.models import MealLog
from logs.serializers import MealLogSerializer


def _parse_date_param(raw: str) -> date_type:
    """Parse a ?date= value, raising a 400 (not a 500 / silent None) if malformed."""
    try:
        parsed = parse_date(raw)  # None if unparseable; ValueError if out of range
    except ValueError:
        parsed = None
    if parsed is None:
        raise ValidationError({"date": "invalid date; expected YYYY-MM-DD"})
    return parsed


class MealLogListCreate(generics.ListCreateAPIView[MealLog]):
    serializer_class = MealLogSerializer

    def get_queryset(self) -> QuerySet[MealLog]:
        assert isinstance(self.request.user, User)
        queryset = MealLog.objects.filter(user=self.request.user)
        date = self.request.query_params.get("date")
        if date:
            queryset = queryset.filter(logged_at__date=_parse_date_param(date))
        return queryset

    def perform_create(self, serializer: BaseSerializer[MealLog]) -> None:
        serializer.save(user=self.request.user)


class MealLogDetail(generics.RetrieveDestroyAPIView[MealLog]):
    """Retrieve or delete a single entry — scoped to its owner (404 for others)."""

    serializer_class = MealLogSerializer

    def get_queryset(self) -> QuerySet[MealLog]:
        assert isinstance(self.request.user, User)
        return MealLog.objects.filter(user=self.request.user)


class DailySummaryView(APIView):
    def get(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        date_param = request.query_params.get("date")
        day = _parse_date_param(date_param) if date_param else timezone.now().date()
        logs = MealLog.objects.filter(user=request.user, logged_at__date=day)
        totals = logs.aggregate(
            kcal=Sum("kcal"),
            protein=Sum("protein_g"),
            carbs=Sum("carbs_g"),
            fat=Sum("fat_g"),
        )
        total: int = totals["kcal"] or 0
        goal = request.user.daily_calorie_goal
        summary: dict[str, Any] = {
            "date": str(day),
            "total_kcal": total,
            "goal": goal,
            "remaining": goal - total,
            "protein_g": float(totals["protein"] or 0),
            "carbs_g": float(totals["carbs"] or 0),
            "fat_g": float(totals["fat"] or 0),
            "count": logs.count(),
        }
        return Response(summary)
